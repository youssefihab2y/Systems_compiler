def extract_block_info(symb_table_file):
    """Extract block information from symbol table."""
    print("\n=== Extracting Block Information ===")
    block_info = []
    try:
        with open(symb_table_file, 'r') as f:
            lines = f.readlines()
            in_block_section = False
            
            for line in lines:
                if "Block name" in line:
                    print("Found block section")
                    in_block_section = True
                    continue
                if in_block_section and line.strip() and "Symbol" not in line:
                    parts = line.strip().split('\t')
                    if len(parts) >= 4:
                        name = parts[0].replace("(Default)", "0")
                        block_info.append({
                            "Block": name,
                            "Address": parts[2],
                            "Length": parts[3]
                        })
                        print(f"Added block: {name}, Address: {parts[2]}, Length: {parts[3]}")
                if "Symbol" in line:
                    print("End of block section")
                    break
    except Exception as e:
        print(f"Error reading symbol table: {e}")
        return []
    
    print(f"Extracted {len(block_info)} blocks")
    return block_info

def generate_htme_records(pass2_content, htme_output_file, block_info, program_name="FIRST"):
    """Generate HTME records from Pass2 output."""
    print("\n=== Starting HTME Record Generation ===")
    start_address = 0
    text_records = []
    modification_records = []  # For storing M records
    current_text_record = []
    current_start = None
    current_length = 0
    current_block = None

    for line in pass2_content:
        print(f"\nProcessing line: {line.strip()}")
        
        # Skip header or empty lines
        if not line.strip() or line.startswith("Loc"):
            print("Skipping header or empty line")
            continue

        try:
            # Parse fixed-width columns
            loc = line[0:8].strip()
            block = line[8:13].strip()
            symbols = line[13:25].strip()
            instr = line[25:35].strip()
            reference = line[35:50].strip()
            obj_code = line[50:].strip()

            if not loc.isalnum():
                print("Skipping invalid line")
                continue

            loc = int(loc, 16)
            print(f"Location: {loc:X}, Block: {block}, Instruction: {instr}, Reference: {reference}, Object Code: {obj_code}")

            # Check for Format 4 instructions (starting with +)
            if instr.startswith('+') and obj_code:
                # Add modification record for Format 4 instructions
                mod_location = loc + 1  # Skip the first byte (opcode)
                mod_length = "05"  # Format 4 is 5 half-bytes
                modification_records.append((mod_location, mod_length))
                print(f"Added modification record for Format 4 instruction: loc={mod_location:06X}, len={mod_length}")

            # Start new text record if we switch blocks or encounter USE
            if current_text_record and (
                instr == "USE" or  # Start new record on USE directive
                (current_block is not None and block != current_block)  # or when block changes
            ):
                print(f"Creating new text record due to block change or USE directive")
                text_records.append((current_start, current_length, "".join(current_text_record)))
                current_text_record = []
                current_length = 0
                current_start = None

            current_block = block

            # Skip lines without object code or with directives
            if not obj_code or instr in ["USE", "EQU", "LTORG"]:
                print(f"Skipping directive or empty object code: {instr}")
                continue

            # Clean object code - remove any spaces
            obj_code = obj_code.replace(" ", "")
            
            # Skip if the object code column is empty or contains a symbol
            if not all(c in '0123456789ABCDEF' for c in obj_code):
                print(f"Skipping invalid object code: {obj_code}")
                continue

            # Convert BYTE constants
            if instr == "BYTE" and obj_code.startswith("C'"):
                char = obj_code[2:-1]
                obj_code = "".join(f"{ord(c):02X}" for c in char)
                print(f"Converted BYTE constant to: {obj_code}")

            # Start new text record if needed
            if (instr in ["RESW", "RESB"] or 
                current_length + len(obj_code) // 2 > 30 or 
                not current_text_record):
                
                if current_text_record:
                    print(f"Creating new text record - Start: {current_start:X}, Length: {current_length}")
                    text_records.append((current_start, current_length, "".join(current_text_record)))
                    current_text_record = []
                    current_length = 0
                
                if not instr in ["RESW", "RESB"]:
                    current_start = loc
                    print(f"Setting new text record start address: {loc:X}")

            # Add only actual object code if not RESW/RESB
            if not instr in ["RESW", "RESB"]:
                # Only add if it's a valid object code (not a symbol)
                if all(c in '0123456789ABCDEF' for c in obj_code):
                    current_text_record.append(obj_code)
                    current_length += len(obj_code) // 2
                    print(f"Added object code: {obj_code}, Current length: {current_length}")
                else:
                    print(f"Invalid object code format: {obj_code}")

        except (ValueError, IndexError) as e:
            print(f"Error processing line: {e}")
            continue

    # Write final text record if any remains
    if current_text_record:
        print(f"\nWriting final text record - Start: {current_start:X}, Length: {current_length}")
        text_records.append((current_start, current_length, "".join(current_text_record)))

    # Get program length from the last location (loc is already an integer)
    try:
        program_length = loc  # Changed from int(loc, 16) to just loc
        print(f"\nProgram length: {program_length:X}")
    except (ValueError, IndexError) as e:
        print(f"Error getting program length: {e}")
        return

    print("\n=== Writing HTME Records to File ===")
    with open(htme_output_file, 'w') as f:
        # Write header record
        header = f"H.{program_name:<6}.{start_address:06X}.{program_length:06X}"
        print(f"Header record: {header}")
        f.write(f"{header}\n")
        
        # Write text records
        for start, length, obj_code in text_records:
            text_record = f"T.{start:06X}.{length:02X}.{obj_code}"
            print(f"Text record: {text_record}")
            f.write(f"{text_record}\n")
        
        # Write modification records
        for loc, length in modification_records:
            mod_record = f"M.{loc:06X}.{length}"
            print(f"Modification record: {mod_record}")
            f.write(f"{mod_record}\n")
        
        # Write end record
        end_record = f"E.{start_address:06X}"
        print(f"End record: {end_record}")
        f.write(f"{end_record}\n")

    print(f"\nHTME records written to {htme_output_file}")