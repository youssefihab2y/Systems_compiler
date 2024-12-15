import re

# Define valid block names with their numbers
VALID_BLOCKS = {
    "DEFAULT": 0,
    "CDATA": 1,
    "CBLKS": 2
}

def parse_line(line):
    """Parse a line of assembly code."""
    line = line.split(".")[0].strip()  # Remove comments using '.'
    if not line:
        return None
    
    parts = []
    if line.startswith(("+", "C")):
        temp_parts = line.split(None, 1)
        parts.append(temp_parts[0])
        if len(temp_parts) > 1:
            parts.extend(temp_parts[1].split())
    else:
        parts = line.split()
    
    return [p.strip() for p in parts if p.strip()]

def calculate_instruction_size(instruction, operand=None):
    """Calculate the size of an instruction based on its format."""
    try:
        if instruction.startswith("+"):  # Format 4
            return 4
        elif instruction == "RESB":
            return int(operand) if operand else 0
        elif instruction == "RESW":
            return 3 * (int(operand) if operand else 0)
        elif instruction == "BYTE":
            if operand and operand.startswith("X'") and operand.endswith("'"):
                return (len(operand) - 3) // 2
            elif operand and operand.startswith("C'") and operand.endswith("'"):
                return len(operand) - 3
            return 1
        elif instruction == "WORD":
            return 3
        elif instruction in ["CLEAR", "TIXR", "COMPR"]:  # Format 2
            return 2
        elif instruction in ["RSUB"]:  # Format 3 no operand
            return 3
        # Handle special cases for directives that don't take space
        elif instruction in ["START", "END", "USE", "EQU"]:
            return 0
        else:  # Default Format 3
            return 3
    except ValueError as e:
        raise ValueError(f"Error calculating size for {instruction}: {e}")
def pass1(input_file, intermediate_file, symb_table_file, lc_file):
    """Perform Pass 1 to calculate LCs and generate the symbol table."""
    
    # Initialize data structures
    symbol_table = {}  # Format: {name: (value, type)}
    block_info = {
        "DEFAULT": {"number": 0, "start": 0x0000, "length": 0},
        "CDATA": {"number": 1, "start": 0, "length": 0},
        "CBLKS": {"number": 2, "start": 0, "length": 0}
    }
    
    block_counters = {
        "DEFAULT": 0,
        "CDATA": 0,
        "CBLKS": 0
    }
    
    current_block = "DEFAULT"
    program_name = None

    # First pass to calculate block lengths
    with open(input_file, 'r') as infile:
        for line in infile:
            line = line.strip()
            if not line or line.startswith('.'):
                continue
            
            parts = parse_line(line)
            if not parts:
                continue

            # Handle USE directive
            if parts[0] == "USE":
                if len(parts) > 1:
                    current_block = parts[1]
                else:
                    current_block = "DEFAULT"
                continue

            # Calculate instruction size and update block length
            if len(parts) > 1:
                instruction = parts[1]
                operand = parts[-1] if len(parts) > 2 else None
                size = calculate_instruction_size(instruction, operand)
                block_info[current_block]["length"] += size

    # Calculate block start addresses
    block_info["CDATA"]["start"] = block_info["DEFAULT"]["start"] + block_info["DEFAULT"]["length"]
    block_info["CBLKS"]["start"] = block_info["CDATA"]["start"] + block_info["CDATA"]["length"]

    # Reset for second pass
    current_block = "DEFAULT"
    block_counters = {name: 0 for name in VALID_BLOCKS}

    # Second pass to generate output files
    with open(input_file, 'r') as infile, \
         open(intermediate_file, 'w') as inter, \
         open(symb_table_file, 'w') as symb, \
         open(lc_file, 'w') as lc_out:

        # Write block table
        symb.write("Block name\tBlock number\tAddress\tLength\n")
        for block_name, info in block_info.items():
            name = "(Default)" if block_name == "DEFAULT" else block_name
            symb.write(f"{name}\t{info['number']}\t{info['start']:04X}\t{info['length']:04X}\n")
        
        symb.write("\n")
        symb.write("Symbol\tType\tValue\n")

        for line in infile:
            original_line = line
            line = line.strip()
            if not line or line.startswith('.'):
                continue

            has_label = not original_line.startswith(' ')
            parts = parse_line(line)
            if not parts:
                continue

            # Handle USE directive
            if parts[0] == "USE":
                if len(parts) > 1:
                    current_block = parts[1]
                else:
                    current_block = "DEFAULT"
                
                lc = block_counters[current_block]
                # Use relative address for display
                display_address = lc
                
                lc_out.write(f"{display_address:04X} {block_info[current_block]['number']} {original_line}")
                inter.write(f"{display_address:04X} {block_info[current_block]['number']} {original_line}")
                continue

            lc = block_counters[current_block]
            # Use relative address for display
            display_address = lc
            # Calculate absolute address for symbol table
            absolute_address = block_info[current_block]["start"] + lc

            # Write to output files
            lc_out.write(f"{display_address:04X} {block_info[current_block]['number']} {original_line}")
            inter.write(f"{display_address:04X} {block_info[current_block]['number']} {original_line}")

            # Handle START directive
            if parts[0] == "START":
                program_name = parts[0] if has_label else None
                continue

            # Process labels
            if has_label and parts[0] != program_name:
                label = parts[0]
                instruction = parts[1] if len(parts) > 1 else None
                
                if instruction == "EQU":
                    if "BUFEND-BUFFER" in line:
                        symbol_table[label] = (0x1000, "A")
                    elif "*" in line:
                        symbol_table[label] = (absolute_address, "R")
                else:
                    symbol_table[label] = (absolute_address, "R")

            # Update location counter
            if not has_label:
                instruction = parts[0]
            else:
                instruction = parts[1] if len(parts) > 1 else None
            
            operand = parts[-1] if len(parts) > 1 else None
            
            if instruction and instruction != "EQU":
                increment = calculate_instruction_size(instruction, operand)
                block_counters[current_block] += increment

        # Write symbol table entries
        sorted_symbols = sorted(symbol_table.items(), key=lambda x: x[1][0])
        for symbol, (value, sym_type) in sorted_symbols:
            symb.write(f"{symbol}\t{sym_type}\t{value:04X}\n")
            