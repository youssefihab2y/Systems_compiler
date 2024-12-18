import os
from pass1.instructionSet import Mnemonic as OPCODE_TABLE

# Register mapping
REGISTERS = {
    'A': '0', 'X': '1', 'L': '2', 'B': '3',
    'S': '4', 'T': '5', 'F': '6'
}

# Condition flags mapping
CONDITION_FLAGS = {
    'Z': '00',  # Negative
    'N': '01',  # Zero
    'C': '10',  # Positive
    'V': '11'   # Equal
}

def pass2(intermediate_file, symb_table_file, output_file):
    """Main pass2 function that will be called from main.py"""
    symbol_table = load_symbol_table(symb_table_file)
    literal_table = load_literal_table(symb_table_file)
    base_register = None
    
    with open(intermediate_file, 'r') as f:
        input_lines = [line.strip() for line in f.readlines() if line.strip()]
        input_lines = list(dict.fromkeys(input_lines))

    output_lines = []
    output_lines.append("Loc   Block    Symbols      Instr       Reference        Object Code")

    for line in input_lines[1:]:
        parts = line.split()
        if len(parts) < 2:
            continue

        location = parts[0][:4]
        block = parts[0][4:] if len(parts[0]) > 4 else parts[1]

        label = ''
        instruction = ''
        operand = ''
        object_code = ''

        remaining_parts = parts[1:] if len(parts[0]) > 4 else parts[2:]
        
        if remaining_parts:
            if len(remaining_parts) == 1:
                instruction = remaining_parts[0]
            else:
                if len(remaining_parts) >= 2 and remaining_parts[1] in ['START', 'END', 'RESW', 'RESB', 'BYTE', 'WORD', 'BASE', 'USE'] + list(OPCODE_TABLE.keys()):
                    label = remaining_parts[0]
                    instruction = remaining_parts[1]
                    if len(remaining_parts) > 2:
                        operand = remaining_parts[2]
                else:
                    instruction = remaining_parts[0]
                    if len(remaining_parts) > 1:
                        operand = remaining_parts[1]

        # Handle literals in LTORG section
        if instruction == '*':
            if operand and operand.startswith('='):
                if operand.startswith('=C\'') and operand.endswith('\''):
                    chars = operand[3:-1]
                    object_code = ''.join([format(ord(c), '02X') for c in chars])
                elif operand.startswith('=X\'') and operand.endswith('\''):
                    object_code = operand[3:-1]
        elif instruction == 'BASE':
            if operand in symbol_table:
                base_register = symbol_table[operand]
        elif instruction == 'BYTE':
            object_code = handle_byte_directive(operand)
        elif instruction == 'WORD':
            try:
                value = int(operand)
                object_code = format(value, '06X')
            except ValueError:
                print(f"ERROR: Invalid WORD operand: {operand}")
                object_code = None
        elif instruction in OPCODE_TABLE or (instruction.startswith('+') and instruction[1:] in OPCODE_TABLE):
            object_code = generate_object_code(location, instruction, operand, symbol_table, literal_table, base_register)

        output_line = f"{location:<8}"
        output_line += f"{block:<8}"
        output_line += f"{label:<12}"
        output_line += f"{instruction:<14}"

        if instruction == 'RSUB':
            output_line += " "*15
        elif operand:
            output_line += f"{operand:<15}"
        else:
            output_line += " "*15
            
        if object_code:
            output_line += f"{object_code}"
            
        output_lines.append(output_line)

    with open(output_file, 'w') as f:
        for line in output_lines:
            f.write(line + '\n')

def generate_4f_object_code(opcode, register, condition, address):
    opcode_bin = format(int(opcode, 16), '08b')[:-2]
    reg_hex = REGISTERS.get(register, '0')
    reg_bin = format(int(reg_hex, 16), '04b')
    
    first_byte = format(int(opcode_bin + reg_bin[:2], 2), '02X')
    second_byte = format(int(reg_bin[2:] + condition, 2), '01X')
    
    if isinstance(address, str):
        try:
            addr_hex = format(int(address, 16), '04X').zfill(5)
        except ValueError as e:
            print(f"Error converting address: {e}")
            raise
    else:
        addr_hex = format(address, '04X').zfill(5)
    
    return f"{first_byte}{second_byte}{addr_hex}"

def parse_4f_instruction(instruction, operand):
    parts = operand.replace(',', ' ').split() if operand else []
    
    if len(parts) > 0 and parts[0] in REGISTERS:
        register = parts[0]
        address = parts[1] if len(parts) > 1 else '0'
        flag = parts[2] if len(parts) > 2 else 'N'
    else:
        register = 'A'
        address = parts[0] if len(parts) > 0 else '0'
        flag = parts[1] if len(parts) > 1 else 'N'
    
    if flag in ['00', '01', '10', '11']:
        condition = flag
    else:
        condition = CONDITION_FLAGS.get(flag, '00')
    
    return instruction, register, address, condition

def handle_4f_instruction(instruction, operand, symbol_table):
    opcode, register, address, condition = parse_4f_instruction(instruction, operand)
    
    if address in symbol_table:
        address = symbol_table[address]
    
    opcode_value = OPCODE_TABLE[instruction][1][2:]
    
    return generate_4f_object_code(opcode_value, register, condition, address)

def load_symbol_table(symb_table_file):
    symbol_table = {}
    with open(symb_table_file, 'r') as f:
        lines = f.readlines()
        symbol_section = False
        for line in lines:
            if line.startswith('Symbol\tValue'):
                symbol_section = True
                continue
            if symbol_section and line.strip():
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    symbol = parts[0]
                    value = parts[1]
                    symbol_table[symbol] = value
    return symbol_table

def load_literal_table(symb_table_file):
    literal_table = {}
    with open(symb_table_file, 'r') as f:
        lines = f.readlines()
        literal_section = False
        for line in lines:
            if line.startswith('Literal\tLength\tAddress\tValue'):
                literal_section = True
                continue
            if literal_section and line.strip():
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    literal = parts[0]
                    address = parts[2]
                    value = parts[3]
                    literal_table[literal] = (address, value)
    return literal_table

def get_opcode_value(opcode):
    if isinstance(opcode, list):
        format_type = opcode[0]
        opcode_val = int(opcode[1], 16)
        if format_type in [1, 2]:
            return opcode_val
        binary = format(opcode_val, '08b')[:-2]
        return int(binary, 2)
    
    opcode_val = int(opcode, 16)
    binary = format(opcode_val, '08b')[:-2]
    return int(binary, 2)

def get_instruction_format(instruction, opcode):
    if isinstance(opcode, list):
        return opcode[0]
    if instruction in OPCODE_TABLE and isinstance(OPCODE_TABLE[instruction], list) and OPCODE_TABLE[instruction][0] == '4F':
        return '4F'
    return 3

def parse_operand(operand):
    if not operand:
        return None, None
    
    if operand.startswith('#'):
        value = operand[1:]
        return 'immediate', value
    elif operand.startswith('@'):
        return 'indirect', operand[1:]
    elif ',X' in operand:
        return 'indexed', operand.split(',')[0]
    else:
        return 'simple', operand

def calculate_flags(mode):
    if mode == 'immediate':
        return 0, 1
    elif mode == 'indirect':
        return 1, 0
    else:
        return 1, 1

def handle_byte_directive(operand):
    if operand.startswith('X\'') and operand.endswith('\''):
        return operand[2:-1]
    elif operand.startswith('C\'') and operand.endswith('\''):
        chars = operand[2:-1]
        hex_values = ''.join([format(ord(c), '02X') for c in chars])
        return hex_values
    return None

def calculate_displacement(target_address, current_location, format_type, base_register=None):
    if format_type == 4:
        return target_address, 0, 0, 1
    
    try:
        pc = int(current_location, 16) + 3
        
        if isinstance(target_address, str):
            target_address = int(target_address, 16)
            
        disp = target_address - pc
        
        if -2048 <= disp <= 2047:
            return disp, 0, 1, 0
        elif base_register and 0 <= (target_address - int(base_register, 16)) <= 4095:
            return target_address - int(base_register, 16), 1, 0, 0
        else:
            return target_address & 0xFFF, 0, 0, 0
            
    except ValueError as e:
        raise

def generate_object_code(location, instruction, operand, symbol_table, literal_table, base_register=None):
    is_format_4 = instruction.startswith('+')
    if is_format_4:
        instruction = instruction[1:]

    if instruction == 'RSUB':
        return '4F0000'

    if instruction not in OPCODE_TABLE:
        print(f"WARNING: Instruction {instruction} not found in OPCODE_TABLE")
        return None

    if isinstance(OPCODE_TABLE[instruction], list) and OPCODE_TABLE[instruction][0] == '4F':
        return handle_4f_instruction(instruction, operand, symbol_table)

    opcode = OPCODE_TABLE[instruction]
    format_type = get_instruction_format(instruction, opcode)
    
    if format_type == 1:
        opcode_value = int(opcode[1], 16)
        object_code = format(opcode_value, '02X')
        return object_code

    if is_format_4:
        format_type = 4

    if format_type == 2:
        opcode_val = int(opcode[1], 16) if isinstance(opcode, list) else int(opcode, 16)
        
        if not operand:
            return format(opcode_val, '02X') + '00'
            
        if ',' in operand:
            r1, r2 = operand.split(',')
            r1_val = REGISTERS[r1] if r1 in REGISTERS else r1[-1]
            r2_val = REGISTERS[r2] if r2 in REGISTERS else r2[-1]
            result = format(opcode_val, '02X') + str(r1_val) + str(r2_val)
            return result
        else:
            r1_val = REGISTERS[operand.strip()]
            result = format(opcode_val, '02X') + r1_val + '0'
            return result

    mode, operand_value = parse_operand(operand)
    n, i = calculate_flags(mode)
    x = 1 if mode == 'indexed' else 0
    b = 0
    p = 0

    opcode_val = get_opcode_value(opcode)
    opcode_val = opcode_val & 0b111111
    opcode_ni = (opcode_val << 2) | (n << 1) | i

    target_address = 0
    if operand_value:
        if mode == 'immediate':
            if operand_value.isdigit() or (operand_value.startswith('-') and operand_value[1:].isdigit()):
                target_address = int(operand_value)
                if format_type == 3:
                    return format(opcode_ni, '02X') + '0' + format(target_address, '03X').zfill(3)
                else:
                    flags = 1
                    return format(opcode_ni, '02X') + format(flags, '01X') + format(target_address, '05X').zfill(5)
            elif operand_value in symbol_table:
                target_address = int(symbol_table[operand_value], 16)
        else:
            if operand_value.startswith('='):
                if operand_value in literal_table:
                    literal_address, literal_value = literal_table[operand_value]
                    target_address = int(literal_address, 16)
                    
                    disp, b, p, e = calculate_displacement(target_address, location, format_type, base_register)
                    flags = (x << 3) | (b << 2) | (p << 1) | e
                    
                    if format_type == 3:
                        masked_disp = disp & 0xFFF
                        result = format(opcode_ni, '02X') + format(flags, '01X') + format(masked_disp, '03X')
                    else:
                        masked_addr = target_address & 0xFFFFF
                        result = format(opcode_ni, '02X') + format(flags, '01X') + format(masked_addr, '05X')
                    
                    return result

            elif operand_value in symbol_table:
                target_address = int(symbol_table[operand_value], 16)

    disp, b, p, e = calculate_displacement(target_address, location, format_type, base_register)
    flags = (x << 3) | (b << 2) | (p << 1) | e

    if format_type == 3:
        result = format(opcode_ni, '02X') + format(flags, '01X') + format(disp & 0xFFF, '03X')
        return result
    else:
        result = format(opcode_ni, '02X') + format(flags, '01X') + format(target_address & 0xFFFFF, '05X')
        return result
