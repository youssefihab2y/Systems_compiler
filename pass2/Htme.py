def generate_htme_records(pass2_content, htme_output_file, block_info, program_name="COPYXX"):
    """
    Generate HTME records from Pass2 output.
    Handles:
    - Block-based address adjustment.
    - New T records for block changes, RESW, RESB, and byte cap (30 bytes).
    - Program length as the sum of all block lengths.

    Arguments:
        pass2_content: List of lines from the Pass2 output file.
        htme_output_file: Path to the output HTME file.
        block_info: List of dictionaries containing block info (Block, Address, Length).
        program_name: Name of the program for the H record.

    Output:
        HTME file containing H, T, and E records.
    """
    start_address = None
    text_records = []
    current_text_record = []
    current_start = None
    current_length = 0

    # Extract block starting addresses
    block_start_addresses = {block['Block']: int(block['Address'], 16) for block in block_info}

    # Parsing Pass2 output for HTME generation
    for i, line in enumerate(pass2_content):
        if i == 0:  # Skip header line
            continue

        parts = line.split()
        if len(parts) < 2 or not parts[0].isdigit():
            continue  # Skip invalid lines

        loc = int(parts[0], 16)  # Location counter as integer
        block = parts[1]
        instr = parts[3] if len(parts) > 3 else ""
        obj_code = parts[-1] if len(parts[-1]) > 0 and len(parts[-1]) % 2 == 0 else None

        # Adjusted start address = location + block start address
        adjusted_start = loc + block_start_addresses.get(block, 0)

        # Start a new Text Record for block changes, reserved directives, or byte cap
        if instr in ("RESB", "RESW") or current_length >= 60 or block not in block_start_addresses:
            if current_text_record:
                text_records.append((current_start, current_length, " ".join(current_text_record)))
                current_text_record = []
                current_length = 0
            current_start = f"{adjusted_start:06X}"

        # Set start address for the header
        if not start_address:
            start_address = f"{adjusted_start:06X}"

        # Add object code to the current Text Record
        if obj_code:
            if current_length + len(obj_code) > 60:  # Cap at 30 bytes
                text_records.append((current_start, current_length, " ".join(current_text_record)))
                current_text_record = [obj_code]
                current_start = f"{adjusted_start:06X}"
                current_length = len(obj_code)
            else:
                if not current_text_record:
                    current_start = f"{adjusted_start:06X}"
                current_text_record.append(obj_code)
                current_length += len(obj_code)

    # Append the last Text Record
    if current_text_record:
        text_records.append((current_start, current_length, " ".join(current_text_record)))

    # Calculate total program length as the sum of all block lengths
    program_length = sum(block['Length'] for block in block_info)

    # Writing HTME records
    with open(htme_output_file, 'w') as outfile:
        # Header Record
        outfile.write(f"H.{program_name:6}.{start_address}.{program_length:06X}\n")

        # Text Records
        for record in text_records:
            start, _, codes = record
            length = len(codes.replace(" ", "")) // 2  # True byte length
            outfile.write(f"T.{start}.{length:02X}.{codes}\n")

        # End Record
        outfile.write(f"E.{start_address}\n")

    print("HTME records successfully generated.")

# Example usage
if __name__ == "__main__":
    # Example input: Pass2 output and block information
    pass2_output_file = "path/to/out_pass2.txt"
    htme_output_file = "path/to/HTME.txt"

    # Block Information
    block_info = [
        {"Block": "0", "Address": "0000", "Length": 0x64},
        {"Block": "1", "Address": "0064", "Length": 0},
        {"Block": "2", "Address": "0064", "Length": 0x0B},
        {"Block": "3", "Address": "006F", "Length": 0x1000}
    ]

    # Read Pass2 output file
    with open(pass2_output_file, 'r') as file:
        pass2_content = file.readlines()

    # Generate HTME records
    generate_htme_records(pass2_content, htme_output_file, block_info)