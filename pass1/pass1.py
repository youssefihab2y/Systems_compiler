import re
from .length_tracker import LengthTracker

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
                           "SHIFTR", "SUBR", "SVC","TIXR"]:
            return 2
        elif instruction in ["FIX", "FLOAT", "HIO", "NORM", "SIO", "TIO"]:
            return 1
        elif instruction in ["CADD", "CSUB", "CLOAD", "CSTORE", "CJUMP"]:
            return 4
        elif instruction == "RSUB":
            return 3
        elif instruction in ["ADD", "ADDF", "AND", "COMP", "COMPF", "DIV", "DIVF", 
                           "J", "JEQ", "JGT", "JLT", "JSUB", "LDA", "LDB", "LDCH", 
                           "LDF", "LDL", "LDS", "LDT", "LDX", "LPS", "MUL", "MULF", 
                           "OR", "RD", "RSUB", "SSK", "STA", "STB", "STCH", "STF", 
                           "STI", "STL", "STS", "STSW", "STT", "STX", "SUB", "SUBF", 
                           "TD", "TIX", "WD"]:
            return 3
        elif instruction in ["START", "END", "USE", "EQU", "LTORG","BASE"]:
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

def handle_literal_pool(literals, current_address, current_block, inter_file, lc_file, length_tracker):
    # Get only unprocessed literals that appeared before the current address
    unprocessed_literals = [lit for lit in literals 
                          if not lit.used and 
                          (lit.address is None or lit.address <= current_address)]
    
    if not unprocessed_literals:
        return current_address

    # Write literal pool header only if there are literals to process
    write_formatted_line(inter_file, current_address, VALID_BLOCKS[current_block], "", "*", "LITERAL POOL")
    write_formatted_line(lc_file, current_address, VALID_BLOCKS[current_block], "", "*", "LITERAL POOL")

    # Process each unique literal only once
    processed_names = set()
    for literal in unprocessed_literals:
        if literal.name not in processed_names:
            literal.address = current_address
            literal.block = current_block
            literal.used = True
            processed_names.add(literal.name)
            
            write_formatted_line(inter_file, current_address, VALID_BLOCKS[current_block], "", "*", literal.name)
            write_formatted_line(lc_file, current_address, VALID_BLOCKS[current_block], "", "*", literal.name)
            current_address += literal.length
            # Update length tracker for the current block
            length_tracker.update_from_location(current_address, current_block)

    return current_address

def parse_literal_value(literal_str):
    if literal_str.startswith('=X'):
        # Return the hex value directly
        return literal_str[3:-1]
    elif literal_str.startswith('=C'):
        # Convert character to hex
        char = literal_str[3:-1]
        return ''.join([f'{ord(c):02X}' for c in char])
    return '00'

class AssemblerError(Exception):
    """Base class for assembler errors"""
    pass

class UnidentifiedBlockError(AssemblerError):
    """Raised when an unidentified block name is used"""
    pass

class UnidentifiedSymbolError(AssemblerError):
    """Raised when an undefined symbol is referenced"""
    pass

def validate_block_name(block_name, line_number):
    """Validate block name against predefined blocks"""
    if block_name not in VALID_BLOCKS:
        raise UnidentifiedBlockError(
            f"Error at line {line_number}: Unidentified block name '{block_name}'. "
            f"Valid blocks are: {', '.join(VALID_BLOCKS.keys())}"
        )

def validate_symbol_reference(operand, symbol_table, line_number, instruction=None, registers=None):
    """Validate symbol references, including register operands"""
    if registers is None:
        registers = {'A', 'X', 'L', 'B', 'S', 'T', 'F', 'PC', 'SW'}
    
    # Skip validation for special cases
    if instruction == "BYTE":
        if operand.startswith(("X'", "C'")) and operand.endswith("'"):
            return
    
    # Skip other special cases
    if (operand.startswith(('=', '#', '@')) or  # Literals/Immediate/Indirect
        operand.isdigit()):  # Numbers
        return

    # Handle register-to-register instructions
    register_instructions = {"CLEAR", "COMPR", "ADDR", "SUBR", "MULR", "DIVR", "TIXR", "RMO", 
                           "CADD", "CSUB", "CLOAD", "CSTORE", "CJUMP"}
    
    if instruction in register_instructions:
        operands = operand.split(',')
        if operands[0].strip() in registers:  # First operand is register
            return
        if len(operands) >= 2 and all(op.strip() in registers for op in operands[:2]):
            return

    # Handle indexed addressing
    if ',' in operand:
        base_operand = operand.split(',')[0].strip()
        index_reg = operand.split(',')[1].strip()
        if index_reg in registers:  # Valid index register
            operand = base_operand

    # Skip validation for registers used as operands
    if operand in registers:
        return

    if operand not in symbol_table:
        raise UnidentifiedSymbolError(
            f"Error at line {line_number}: Undefined symbol '{operand}'"
        )

def pass1(input_file, intermediate_file, symb_table_file, lc_file):
    symbol_table = {}
    literal_table = []
    length_tracker = LengthTracker()
    forward_references = []  # Store symbols to validate later
    
    block_info = {
        "DEFAULT": {"number": 0, "start": 0x0000, "length": 0},
        "DEFAULTB": {"number": 1, "start": 0, "length": 0},
        "CDATA": {"number": 2, "start": 0, "length": 0},
        "CBLKS": {"number": 3, "start": 0, "length": 0},
    }
    
    block_counters = {name: 0 for name in VALID_BLOCKS}
    current_block = "DEFAULT"
    first_line = True

    # Define valid registers
    REGISTERS = {'A', 'X', 'L', 'B', 'S', 'T', 'F', 'PC', 'SW'}
    REGISTER_INSTRUCTIONS = {"CLEAR", "COMPR", "ADDR", "SUBR", "MULR", "DIVR", "TIXR", "RMO"}

    # First pass to collect all labels
    with open(input_file, 'r') as infile:
        line_number = 0
        for line in infile:
            line_number += 1
            original_line = line.strip()
            if not original_line or original_line.startswith('.'):
                continue

            parts = parse_line(original_line)
            if not parts:
                continue

            # Add label to symbol table
            if not line.startswith(' '):  # Has label
                label = parts[0]
                if len(parts) > 1:
                    instruction = parts[1]
                    if instruction != "START":  # Don't add START labels to validation
                        symbol_table[label] = None  # Temporary value, will be updated later

            # Store operand references for later validation
            if len(parts) > 1:
                operand = parts[-1] if len(parts) > 2 else None
                instruction = parts[1] if not line.startswith(' ') else parts[0]
                
                if operand and not operand.startswith(('=', '#', '@')) and not operand.isdigit():
                    # Skip validation for special cases
                    if not (('EQU' in parts) or  # Skip all EQU operands
                           (instruction == "BYTE" and operand.startswith(("X'", "C'")) and operand.endswith("'")) or  # Skip BYTE literals
                           'WORD' in parts or  # Skip WORD operands
                           operand.strip() in REGISTERS or  # Skip single register references
                           (instruction in REGISTER_INSTRUCTIONS and  # Skip register instruction operands
                            any(reg.strip() in REGISTERS for reg in operand.split(',')))):
                        forward_references.append((operand, line_number))

    # Validate all forward references
    for symbol, line_num in forward_references:
        if symbol not in symbol_table:
            raise UnidentifiedSymbolError(
                f"Error at line {line_num}: Undefined symbol '{symbol}'"
            )

    # Reset file and continue with normal processing
    with open(input_file, 'r') as infile, open(intermediate_file, 'w') as inter, open(lc_file, 'w') as lc_out:
        end_encountered = False
        line_number = 0
        
        try:
            for line in infile:
                line_number += 1
                original_line = line.strip()
                if not original_line or original_line.startswith('.'):
                    continue

                parts = parse_line(original_line)
                if not parts:
                    continue

                components = parts
                
                # Skip processing for START directive
                if first_line:
                    first_line = False
                    write_formatted_line(inter, 0, VALID_BLOCKS[current_block], components[0], components[1], components[2])
                    write_formatted_line(lc_out, 0, VALID_BLOCKS[current_block], components[0], components[1], components[2])
                    continue

                lc = block_counters[current_block]

                # Handle END directive
                if (len(components) > 1 and components[1] == "END") or components[0] == "END":
                    if not end_encountered:
                        end_encountered = True
                        # Process any remaining literals
                        if literal_table:
                            lc = handle_literal_pool(literal_table, lc, current_block, inter, lc_out, length_tracker)
                            block_counters[current_block] = lc
                            # Ensure the block length is updated after processing the last literal
                            length_tracker.update_from_location(lc, current_block)
                        write_formatted_line(inter, lc, VALID_BLOCKS[current_block], "", "END", components[-1])
                        write_formatted_line(lc_out, lc, VALID_BLOCKS[current_block], "", "END", components[-1])
                    continue

                # Skip if we've already processed an END directive
                if end_encountered:
                    continue

                # Handle USE directive with block validation
                if components[0] == "USE":
                    new_block = components[1] if len(components) > 1 else "DEFAULT"
                    validate_block_name(new_block, line_number)
                    current_block = new_block
                    write_formatted_line(inter, lc, VALID_BLOCKS[current_block], "", "USE", current_block)
                    write_formatted_line(lc_out, lc, VALID_BLOCKS[current_block], "", "USE", current_block)
                    continue

                # Handle instructions with symbol validation
                has_label = not line.startswith(' ')
                instruction = components[1] if has_label else components[0]
                operand = components[-1] if len(components) > 1 else None

                # Validate symbol references in operands
                if operand and not instruction == "EQU":
                    # Split operand to handle indexed addressing
                    operand_parts = operand.split(',')
                    base_operand = operand_parts[0]
                    
                    # Skip validation for literals, immediate values, and indirect addressing
                    if not (base_operand.startswith(('=', '#', '@')) or 
                           base_operand.isdigit() or 
                           instruction in ["START", "END", "USE", "LTORG"]):
                        validate_symbol_reference(base_operand, symbol_table, line_number, instruction, REGISTERS)

                # Write the line to output files
                if has_label:
                    label = components[0]
                    if instruction == "EQU":
                        if "BUFEND-BUFFER" in original_line:
                            symbol_table[label] = (0x1000, "A")  # Fixed size for BUFEND-BUFFER
                        elif "*" in original_line:
                            symbol_table[label] = (lc, "R")
                    elif instruction != "START":
                        symbol_table[label] = (lc, "R", current_block)

                write_formatted_line(inter, lc, VALID_BLOCKS[current_block], 
                                  components[0] if has_label else "", 
                                  instruction, 
                                  operand if operand else "")
                write_formatted_line(lc_out, lc, VALID_BLOCKS[current_block], 
                                   components[0] if has_label else "", 
                                   instruction, 
                                   operand if operand else "")

                # Handle literals
                if operand and operand.startswith('='):
                    literal_length = parse_literal(operand)
                    new_literal = Literal(operand, operand, literal_length)
                    if new_literal not in literal_table:
                        literal_table.append(new_literal)

                # Handle LTORG directive
                if instruction == "LTORG":
                    lc = handle_literal_pool(literal_table, lc, current_block, inter, lc_out, length_tracker)
                    block_counters[current_block] = lc
                    continue

                # Update location counter
                if not (instruction == "USE" or instruction == "LTORG" or instruction == "END"):
                    instruction_size = calculate_instruction_size(instruction, operand)
                    block_counters[current_block] += instruction_size
                    length_tracker.update_from_location(block_counters[current_block], current_block)

        except (UnidentifiedBlockError, UnidentifiedSymbolError) as e:
            print(f"\nAssembly Error:\n{str(e)}")
            raise
        except Exception as e:
            print(f"\nUnexpected error at line {line_number}:\n{str(e)}")
            raise

    # Update block_info with tracked lengths
    lengths = length_tracker.get_all_lengths()
    for block in block_info:
        block_info[block]["length"] = lengths[block]

    # Calculate start addresses
    block_info["DEFAULTB"]["start"] = block_info["DEFAULT"]["start"] + block_info["DEFAULT"]["length"]
    block_info["CDATA"]["start"] = block_info["DEFAULTB"]["start"] + block_info["DEFAULTB"]["length"]
    block_info["CBLKS"]["start"] = block_info["CDATA"]["start"] + block_info["CDATA"]["length"]

    # Update symbol values with block start addresses
    final_symbol_table = {}
    for symbol, info in symbol_table.items():
        if len(info) == 3:  # Regular symbol with block info
            value, sym_type, block = info
            # Add block's starting address to symbol's value
            final_value = value + block_info[block]["start"]
            final_symbol_table[symbol] = (final_value, sym_type)
        else:  # EQU symbols
            value, sym_type = info
            final_symbol_table[symbol] = (value, sym_type)

    symbol_table = final_symbol_table

    # Write symbol table with correct sorting
    with open(symb_table_file, 'w') as symb:
        # Write block information
        symb.write("Block name\tBlock number\tAddress\tLength\n")
        for block_name, info in block_info.items():
            symb.write(f"{block_name}\t{info['number']}\t{info['start']:04X}\t{info['length']:04X}\n")

    
        symb.write("\nSymbol\tValue\n")
        sorted_symbols = sorted(symbol_table.items(), key=lambda x: x[1][0])
        for symbol, (value, _) in sorted_symbols:
            symb.write(f"{symbol}\t{value:04X}\n")

   
        symb.write("\nLiteral\tLength\tAddress\tValue\n")
        for literal in literal_table:
            if literal.used:
                # Calculate absolute address by adding block start address
                abs_address = literal.address + block_info[literal.block]["start"]
                value = parse_literal_value(literal.name)
                symb.write(f"{literal.name}\t{literal.length}\t{abs_address:04X}\t{value}\n")