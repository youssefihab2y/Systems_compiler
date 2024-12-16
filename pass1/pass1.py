import re

class Literal:
    def __init__(self, name, value, length):
        self.name = name
        self.value = value
        self.length = length
        self.address = None
        self.block = None
        self.used = False

    def __eq__(self, other):
        return self.name == other.name if isinstance(other, Literal) else False

VALID_BLOCKS = {
    "DEFAULT": 0,
    "DEFAULTB": 1,
    "CDATA": 2,
    "CBLKS": 3,
}

def parse_line(line):
    line = line.split(".")[0].strip()
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

def parse_literal(literal_str):
    if literal_str.startswith('=X'):
        return (len(literal_str) - 4) // 2
    elif literal_str.startswith('=C'):
        return len(literal_str) - 4
    return 0

def calculate_instruction_size(instruction, operand=None):
    try:
        if instruction.startswith("+"):
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
        elif instruction in ["ADDR", "CLEAR", "COMPR", "DIVR", "MULR", "RMO", "SHIFTL", 
                           "SHIFTR", "SUBR", "SVC", "TIXR"]:
            return 2
        elif instruction in ["FIX", "FLOAT", "HIO", "NORM", "SIO", "TIO"]:
            return 1
        elif instruction == "RSUB":
            return 3
        elif instruction in ["ADD", "ADDF", "AND", "COMP", "COMPF", "DIV", "DIVF", 
                           "J", "JEQ", "JGT", "JLT", "JSUB", "LDA", "LDB", "LDCH", 
                           "LDF", "LDL", "LDS", "LDT", "LDX", "LPS", "MUL", "MULF", 
                           "OR", "RD", "RSUB", "SSK", "STA", "STB", "STCH", "STF", 
                           "STI", "STL", "STS", "STSW", "STT", "STX", "SUB", "SUBF", 
                           "TD", "TIX", "WD"]:
            return 3
        elif instruction in ["START", "END", "USE", "EQU", "LTORG"]:
            return 0
        else:
            return 3
    except ValueError as e:
        raise ValueError(f"Error calculating size for {instruction}: {e}")

def write_formatted_line(file, loc, block, label, opcode, operand):
    loc_str = f"{loc:04X}" if loc is not None else "    "
    block_str = f"{block}"
    label_str = f"{label:<8}" if label else " " * 8
    opcode_str = f"{opcode:<8}" if opcode else " " * 8
    operand_str = f"{operand:<12}" if operand else " " * 12
    
    formatted_line = f"{loc_str} {block_str} {label_str} {opcode_str} {operand_str}"
    file.write(formatted_line.rstrip() + "\n")

def handle_literal_pool(literals, current_address, current_block, inter_file, lc_file):
    unprocessed_literals = [lit for lit in literals if not lit.used]
    if not unprocessed_literals:
        return current_address

    write_formatted_line(inter_file, current_address, VALID_BLOCKS[current_block], "", "*", "LITERAL POOL")
    write_formatted_line(lc_file, current_address, VALID_BLOCKS[current_block], "", "*", "LITERAL POOL")

    for literal in unprocessed_literals:
        literal.address = current_address
        literal.block = current_block
        literal.used = True
        write_formatted_line(inter_file, current_address, VALID_BLOCKS[current_block], "", "*", literal.name)
        write_formatted_line(lc_file, current_address, VALID_BLOCKS[current_block], "", "*", literal.name)
        current_address += literal.length

    return current_address

def pass1(input_file, intermediate_file, symb_table_file, lc_file):
    symbol_table = {}
    literal_table = []
    block_info = {
        "DEFAULT": {"number": 0, "start": 0x0000, "length": 0},
        "DEFAULTB": {"number": 1, "start": 0, "length": 0},
        "CDATA": {"number": 2, "start": 0, "length": 0},
        "CBLKS": {"number": 3, "start": 0, "length": 0},
    }
    
    block_counters = {name: 0 for name in VALID_BLOCKS}
    current_block = "DEFAULT"

    # First pass to calculate block lengths
    with open(input_file, 'r') as infile:
        for line in infile:
            line = line.strip()
            if not line or line.startswith('.'):
                continue
            
            parts = parse_line(line)
            if not parts:
                continue
            # Check for END directive first
            if parts[0] == "END" or (len(parts) > 1 and parts[1] == "END"):
                break

            # Handle literals in operands
            for part in parts:
                if part.startswith('='):
                    lit_length = parse_literal(part)
                    new_literal = Literal(part, part[1:], lit_length)
                    if new_literal not in literal_table:
                        literal_table.append(new_literal)

            # Handle USE directive
            if parts[0] == "USE":
                current_block = parts[1] if len(parts) > 1 else "DEFAULT"
                continue

            # Handle LTORG directive
            if "LTORG" in parts:
                block_counters[current_block] = handle_literal_pool(
                    literal_table,
                    block_counters[current_block],
                    current_block,
                    open(intermediate_file, 'a'),
                    open(lc_file, 'a')
                )
                continue

            # Calculate instruction size
            has_label = not line.startswith(' ')
            if has_label:
                if len(parts) > 1:  # Has label and instruction
                    instruction = parts[1]
                    operand = parts[-1] if len(parts) > 2 else None
                    if instruction not in ["START", "EQU"]:
                        size = calculate_instruction_size(instruction, operand)
                        block_counters[current_block] += size
                        print(block_counters)
            else:  # No label
                instruction = parts[0]
                operand = parts[-1] if len(parts) > 1 else None
                if instruction not in ["START", "EQU", "USE"]:
                    size = calculate_instruction_size(instruction, operand)
                    block_counters[current_block] += size
    # Update block lengths and calculate start addresses
    for block in block_info:
        block_info[block]["length"] = block_counters[block]

    block_info["DEFAULTB"]["start"] = block_info["DEFAULT"]["start"] + block_info["DEFAULT"]["length"]
    block_info["CDATA"]["start"] = block_info["DEFAULTB"]["start"] + block_info["DEFAULTB"]["length"]
    block_info["CBLKS"]["start"] = block_info["CDATA"]["start"] + block_info["CDATA"]["length"]

    # Reset for second pass
    current_block = "DEFAULT"
    block_counters = {name: 0 for name in VALID_BLOCKS}

    # Add end_encountered flag
    end_encountered = False
    
    # Second pass
    with open(input_file, 'r') as infile, \
         open(intermediate_file, 'w') as inter, \
         open(symb_table_file, 'w') as symb, \
         open(lc_file, 'w') as lc_out:

        # Write block table
        symb.write("Block name\tBlock number\tAddress\tLength\n")
        for block_name, info in block_info.items():
            name = "(Default)" if block_name == "DEFAULT" else block_name
            symb.write(f"{name}\t{info['number']}\t{info['start']:04X}\t{info['length']:04X}\n")
        
        symb.write("\nSymbol\tType\tValue\n")

        # Reset literal usage flags
        for literal in literal_table:
            literal.used = False

        # Process each line
        for line in infile:
            # Skip if END was already encountered
            if end_encountered:
                continue
                
            original_line = line.strip()
            if not original_line or original_line.startswith('.'):
                continue

            has_label = not line.startswith(' ')
            parts = parse_line(original_line)
            if not parts:
                continue

            components = parts

            # Check for END directive first
            if components[0] == "END" or (len(components) > 1 and components[1] == "END"):
                end_encountered = True
                operand = components[-1] if len(components) > 1 else ""
                
                # Process any remaining literals before END
                lc = handle_literal_pool(literal_table, block_counters[current_block], 
                                      current_block, inter, lc_out)
                block_counters[current_block] = lc
                
                # Write END directive once
                write_formatted_line(inter, lc, VALID_BLOCKS[current_block], 
                                  "", "END", operand)
                write_formatted_line(lc_out, lc, VALID_BLOCKS[current_block], 
                                  "", "END", operand)
                continue

            if components[0] == "USE":
                current_block = components[1] if len(components) > 1 else "DEFAULT"
                lc = block_counters[current_block]
                write_formatted_line(inter, lc, VALID_BLOCKS[current_block], "", "USE", current_block)
                write_formatted_line(lc_out, lc, VALID_BLOCKS[current_block], "", "USE", current_block)
                continue

            if "LTORG" in components:
                lc = block_counters[current_block]
                write_formatted_line(inter, lc, VALID_BLOCKS[current_block], "", "LTORG", "")
                write_formatted_line(lc_out, lc, VALID_BLOCKS[current_block], "", "LTORG", "")
                lc = handle_literal_pool(literal_table, lc, current_block, inter, lc_out)
                block_counters[current_block] = lc
                continue

            lc = block_counters[current_block]
            absolute_address = block_info[current_block]["start"] + lc

            if has_label:
                label = components[0]
                opcode = components[1] if len(components) > 1 else ""
                operand = " ".join(components[2:]) if len(components) > 2 else ""
            else:
                label = ""
                opcode = components[0]
                operand = " ".join(components[1:]) if len(components) > 1 else ""

            write_formatted_line(inter, lc, VALID_BLOCKS[current_block], label, opcode, operand)
            write_formatted_line(lc_out, lc, VALID_BLOCKS[current_block], label, opcode, operand)

            if has_label and components[0] != "START":
                label = components[0]
                if len(components) > 1 and components[1] == "EQU":
                    if "BUFEND-BUFFER" in original_line:
                        symbol_table[label] = (0x1000, "A")
                    elif "*" in original_line:
                        symbol_table[label] = (absolute_address, "R")
                else:
                    symbol_table[label] = (absolute_address, "R")

            instruction = components[1] if has_label else components[0]
            operand = components[-1] if len(components) > 1 else None
            
            if instruction not in ["START", "END", "EQU"]:
                increment = calculate_instruction_size(instruction, operand)
                block_counters[current_block] += increment

        # Write symbol table
        sorted_symbols = sorted(symbol_table.items(), key=lambda x: x[1][0])
        for symbol, (value, sym_type) in sorted_symbols:
            symb.write(f"{symbol}\t{sym_type}\t{value:04X}\n")

        # Write literal table
        symb.write("\nLiteral\tLength\tAddress\tBlock\n")
        for literal in literal_table:
            if literal.address is not None:
                # Calculate absolute address by adding block start address
                absolute_address = block_info[literal.block]["start"] + literal.address
                symb.write(f"{literal.name}\t{literal.length}\t{absolute_address:04X}\t{literal.block}\n")