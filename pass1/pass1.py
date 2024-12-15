import re

# Define valid block names and their base addresses
VALID_BLOCKS = {
    "DEFAULT": 0x1000,
    "DEFAULTB": 0x2000,
    "CDATA": 0x3000,
    "CBLKS": 0x4000
}

# Initialize block counters with their base addresses
block_counters = {
    "DEFAULT": 0x1000,
    "DEFAULTB": 0x2000,
    "CDATA": 0x3000,
    "CBLKS": 0x4000
}

current_block = "DEFAULT"
literals = {}
symbol_table = {}

def parse_line(line):
    """Parse a line of assembly code."""
    line = line.split(";")[0].strip()
    if not line:
        return None
    
    parts = []
    if line.startswith(("+" , "C")):
        temp_parts = line.split(None, 1)
        parts.append(temp_parts[0])
        if len(temp_parts) > 1:
            parts.extend(temp_parts[1].split(','))
    else:
        temp_parts = line.split(None, 1)
        parts.append(temp_parts[0])
        if len(temp_parts) > 1:
            parts.extend(temp_parts[1].split())
    
    return [p.strip() for p in parts if p.strip()]

def calculate_instruction_size(instruction, operand=None, line=None):
    """Calculate the size of an instruction based on its format."""
    try:
        if instruction.startswith("+"):  # Format 4
            return 4
        elif instruction.startswith("C") and instruction in ["CADD", "CSUB", "CLOAD", "CSTORE", "CJUMP"]:
            return 4
        elif instruction == "RESB":
            return int(operand) if operand else 0
        elif instruction == "RESW":
            return 3 * (int(operand) if operand else 0)
        elif instruction == "BYTE":
            if operand and operand.startswith("C'") and operand.endswith("'"):
                return len(operand) - 3
            elif operand and operand.startswith("X'") and operand.endswith("'"):
                return (len(operand) - 3) // 2
            return 1
        elif instruction == "WORD":
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

        # Handle START directive
        first_line = next(infile).strip()
        if first_line.startswith("START"):
            start_address = int(first_line.split()[1], 16)
            block_counters["DEFAULT"] = start_address
            lc_out.write(f"     {first_line}\n")
        else:
            raise ValueError("Program must begin with START directive")

        # Process remaining lines
        for line in infile:
            line = line.strip()
            if not line:
                continue

            parts = parse_line(line)
            if not parts:
                continue

            # Handle block directives
            if parts[0] in VALID_BLOCKS:
                current_block = parts[0]
                lc = block_counters[current_block]
                lc_out.write(f"{lc:04X} {line}\n")
                continue

            # Handle END directive
            if parts[0] == "END":
                lc = block_counters[current_block]
                lc_out.write(f"{lc:04X} {line}\n")
                break

            lc = block_counters[current_block]

            # Process label and instruction
            if not parts[0].startswith(("+", "C")) and len(parts) >= 2:
                label, instruction = parts[0], parts[1]
                operand = parts[2] if len(parts) > 2 else None
                symbol_table[label] = lc
            else:
                instruction = parts[0]
                operand = parts[1] if len(parts) > 1 else None

            # Handle literals
            if operand and operand.startswith("="):
                if operand not in literals:
                    literals[operand] = None

            # Write to output files
            lc_out.write(f"{lc:04X} {line}\n")
            inter.write(f"{lc:04X} {instruction} {operand if operand else ''}\n")

            # Update location counter for current block
            increment = calculate_instruction_size(instruction, operand, line)
            block_counters[current_block] = lc + increment

        # Handle literals in CDATA block
        if literals:
            current_block = "CDATA"
            lc = block_counters[current_block]
            for literal in literals:
                literals[literal] = lc
                lc += calculate_instruction_size("BYTE", literal[1:])
            block_counters["CDATA"] = lc

        # Write symbol table
        for label, addr in symbol_table.items():
            symb.write(f"{label} {addr:04X}\n")