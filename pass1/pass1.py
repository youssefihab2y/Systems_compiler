import re

# Define valid block names with their numbers
VALID_BLOCKS = {
    "DEFAULT": 0,
    "CDATA": 1,
    "CBLKS": 2
}

# Initialize block counters
block_counters = {
    "DEFAULT": 0,
    "CDATA": 0,
    "CBLKS": 0
}

current_block = "DEFAULT"
literals = {}
symbol_table = {}

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
            if operand.startswith("X'") and operand.endswith("'"):
                return (len(operand) - 3) // 2
            elif operand.startswith("C'") and operand.endswith("'"):
                return len(operand) - 3
            return 1
        elif instruction == "WORD":
            return 3
        elif instruction in ["CLEAR", "TIXR"]:  # Format 2
            return 2
        elif instruction in ["RSUB"]:  # Format 3 no operand
            return 3
        else:
            return 3
    except ValueError as e:
        raise ValueError(f"Error calculating size for {instruction}: {e}")

def pass1(input_file, intermediate_file, symb_table_file, lc_file):
    """Perform Pass 1 to calculate LCs and generate the symbol table."""
    global current_block
    
    with open(input_file, 'r') as infile, \
         open(intermediate_file, 'w') as inter, \
         open(symb_table_file, 'w') as symb, \
         open(lc_file, 'w') as lc_out:

        # Process each line
        for line in infile:
            line = line.strip()
            if not line:
                continue

            parts = parse_line(line)
            if not parts:
                continue

            # Get current location counter
            lc = block_counters[current_block]

            # Handle START directive
            if parts[0] == "START":
                start_address = int(parts[1], 16) if len(parts) > 1 else 0
                block_counters["DEFAULT"] = start_address
                lc_out.write(f"{lc:04X} {VALID_BLOCKS[current_block]} {line}\n")
                continue

            # Handle USE directive
            if parts[0] == "USE":
                if len(parts) > 1:
                    current_block = parts[1]
                else:
                    current_block = "DEFAULT"
                lc = block_counters[current_block]
                lc_out.write(f"{lc:04X} {VALID_BLOCKS[current_block]} {line}\n")
                continue

            # Process label and instruction
            if not parts[0].startswith(("+", "USE")):
                label = parts[0]
                instruction = parts[1] if len(parts) > 1 else None
                operand = parts[2] if len(parts) > 2 else None
                
                if instruction:  # This is a label with instruction
                    symbol_table[label] = (lc, current_block)
                else:  # This is just a label
                    instruction = label
                    label = None
                    operand = parts[1] if len(parts) > 1 else None
            else:
                label = None
                instruction = parts[0]
                operand = parts[1] if len(parts) > 1 else None

            # Write to output file
            lc_out.write(f"{lc:04X} {VALID_BLOCKS[current_block]} {line}\n")

            # Handle EQU directive
            if instruction == "EQU":
                continue

            # Update location counter
            if instruction:
                increment = calculate_instruction_size(instruction, operand)
                block_counters[current_block] = lc + increment

        # Write symbol table
        for label, (addr, block) in symbol_table.items():
            symb.write(f"{label} {addr:04X} {VALID_BLOCKS[block]}\n")