import re

class Literal:
    def __init__(self, name, value, length):
        self.name = name
        self.value = value
        self.length = length
        self.address = None
        self.block = None
        self.used = False  # Track if literal has been processed

    def __eq__(self, other):
        return self.name == other.name if isinstance(other, Literal) else False

VALID_BLOCKS = {
    "DEFAULT": 0,
    "DEFAULTB":1,
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
    """Parse literal and return its length"""
    if literal_str.startswith('=X'):
        return (len(literal_str) - 4) // 2  # Remove =X'' and divide by 2
    elif literal_str.startswith('=C'):
        return len(literal_str) - 4  # Remove =C''
    return 0
def load_instruction_set(filename):
    """Load instruction set from file"""
    Mnemonic = {}
    try:
        with open(filename, 'r') as file:
            exec(file.read(), None, {'Mnemonic': Mnemonic})
        return Mnemonic
    except FileNotFoundError:
        print(f"Error: Instruction set file '{filename}' not found")
        return {}
    except Exception as e:
        print(f"Error loading instruction set: {e}")
        return {}

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
        # Format 2 Instructions
        elif instruction in ["ADDR", "CLEAR", "COMPR", "DIVR", "MULR", "RMO", "SHIFTL", 
                           "SHIFTR", "SUBR", "SVC", "TIXR"]:
            return 2
        # Format 1 Instructions
        elif instruction in ["FIX", "FLOAT", "HIO", "NORM", "SIO", "TIO"]:
            return 1
        elif instruction == "RSUB":
            return 3
        # Format 3 Instructions
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
def handle_literal_pool(literals, current_address, current_block, inter_file, lc_file):
    """Process and write literal pool"""
    # Get unprocessed literals
    unprocessed_literals = [lit for lit in literals if not lit.used]
    if not unprocessed_literals:
        return current_address

    # Write literal pool marker
    inter_file.write(f"{current_address:04X} {VALID_BLOCKS[current_block]} * LITERAL POOL\n")
    lc_file.write(f"{current_address:04X} {VALID_BLOCKS[current_block]} * LITERAL POOL\n")

    for literal in unprocessed_literals:
        literal.address = current_address
        literal.block = current_block
        literal.used = True
        # Write literal to intermediate file
        inter_file.write(f"{current_address:04X} {VALID_BLOCKS[current_block]} * {literal.name}\n")
        lc_file.write(f"{current_address:04X} {VALID_BLOCKS[current_block]} * {literal.name}\n")
        current_address += literal.length

    return current_address

def pass1(input_file, intermediate_file, symb_table_file, lc_file):
    # Initialize data structures
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

    # First pass to calculate block lengths and collect literals
    with open(input_file, 'r') as infile:
        for line in infile:
            line = line.strip()
            if not line or line.startswith('.'):
                continue
            
            parts = parse_line(line)
            if not parts:
                continue

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
                block_info[current_block]["length"] = handle_literal_pool(
                    literal_table,
                    block_info[current_block]["length"],
                    current_block,
                    open(intermediate_file, 'a'),
                    open(lc_file, 'a')
                )
                continue

            # Calculate instruction size
            if len(parts) > 1:
                instruction = parts[1]
                operand = parts[-1] if len(parts) > 2 else None
                size = calculate_instruction_size(instruction, operand)
                block_info[current_block]["length"] += size

            # Handle END directive - process remaining literals
            if parts[0] == "END" or (len(parts) > 1 and parts[1] == "END"):
                block_info[current_block]["length"] = handle_literal_pool(
                    literal_table,
                    block_info[current_block]["length"],
                    current_block,
                    open(intermediate_file, 'a'),
                    open(lc_file, 'a')
                )

    # Calculate block start addresses
    block_info["DEFAULTB"]["start"] = block_info["DEFAULT"]["start"] + block_info["DEFAULT"]["length"]
    block_info["CDATA"]["start"] = block_info["DEFAULTB"]["start"] + block_info["DEFAULTB"]["length"]
    block_info["CBLKS"]["start"] = block_info["CDATA"]["start"] + block_info["CDATA"]["length"]


    # Reset for second pass
    current_block = "DEFAULT"
    block_counters = {name: 0 for name in VALID_BLOCKS}

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

        # Reset literal usage flags for second pass
        for literal in literal_table:
            literal.used = False

        # Process each line
        for line in infile:
            original_line = line.strip()
            if not original_line or original_line.startswith('.'):
                continue

            has_label = not line.startswith(' ')
            parts = parse_line(original_line)
            if not parts:
                continue

            # Handle directives and instructions
            if parts[0] == "USE":
                current_block = parts[1] if len(parts) > 1 else "DEFAULT"
                lc = block_counters[current_block]
                inter.write(f"{lc:04X} {VALID_BLOCKS[current_block]} {original_line}\n")
                lc_out.write(f"{lc:04X} {VALID_BLOCKS[current_block]} {original_line}\n")
                continue

            if "LTORG" in parts:
                lc = block_counters[current_block]
                lc = handle_literal_pool(literal_table, lc, current_block, inter, lc_out)
                block_counters[current_block] = lc
                continue

            # Process normal instructions
            lc = block_counters[current_block]
            absolute_address = block_info[current_block]["start"] + lc

            inter.write(f"{lc:04X} {VALID_BLOCKS[current_block]} {original_line}\n")
            lc_out.write(f"{lc:04X} {VALID_BLOCKS[current_block]} {original_line}\n")

            # Handle labels
            if has_label and parts[0] != "START":
                label = parts[0]
                if len(parts) > 1 and parts[1] == "EQU":
                    if "BUFEND-BUFFER" in original_line:
                        symbol_table[label] = (0x1000, "A")
                    elif "*" in original_line:
                        symbol_table[label] = (absolute_address, "R")
                else:
                    symbol_table[label] = (absolute_address, "R")

            # Update location counter
            instruction = parts[1] if has_label else parts[0]
            operand = parts[-1] if len(parts) > 1 else None
            
            if instruction not in ["START", "END", "EQU"]:
                increment = calculate_instruction_size(instruction, operand)
                block_counters[current_block] += increment

            # Handle END directive
            if instruction == "END":
                # Generate final literal pool
                lc = handle_literal_pool(literal_table, lc, current_block, inter, lc_out)

        # Write symbol table
        sorted_symbols = sorted(symbol_table.items(), key=lambda x: x[1][0])
        for symbol, (value, sym_type) in sorted_symbols:
            symb.write(f"{symbol}\t{sym_type}\t{value:04X}\n")

        # Write literal table
        symb.write("\nLiteral\tLength\tAddress\tBlock\n")
        for literal in literal_table:
            if literal.address is not None:
                symb.write(f"{literal.name}\t{literal.length}\t{literal.address:04X}\t{literal.block}\n")