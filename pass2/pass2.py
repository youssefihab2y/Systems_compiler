import os

# Get the directory where the script is located
current_dir = os.path.dirname(os.path.abspath(__file__))

# Import instruction set - correct way
from pass1.instructionSet import Mnemonic as OPCODE_TABLE


# Register mapping
REGISTERS = {
    'A': '0',
    'X': '1',
    'L': '2',
    'B': '3',
    'S': '4',
    'T': '5',
    'F': '6'
}

# Format 4F opcodes
FORMAT_4F_OPCODES = {
    'CADD': '1C',
    # Add other Format 4F opcodes here
}

def generate_4f_object_code(opcode, register, condition, address):
    # Convert register name to hex code
    register_codes = {
        'A': '0',
        'X': '1',
        'L': '2',
        'B': '3',
        'S': '4',
        'T': '5',
        'F': '6'
    }
    
    # Convert condition flag to 2-bit code
    condition_codes = {
        'Z': '00',  # Zero flag
        'N': '01',  # Negative flag
        'C': '10',  # Carry flag
        'V': '11'   # Overflow flag
    }
    
    # Convert components to binary
    opcode_bin = format(int(opcode, 16), '06b')
    register_bin = format(int(register_codes.get(register, '0'), 16), '04b')
    condition_bin = condition_codes.get(condition, '00')
    address_bin = format(int(address, 16), '020b')
    
    # Concatenate all parts
    instruction_bin = opcode_bin + register_bin + condition_bin + address_bin
    
    # Convert to hexadecimal
    instruction_hex = format(int(instruction_bin, 2), '08X')
    
    return instruction_hex

def parse_4f_instruction(instruction, operand):
    """
    Parse a Format 4F instruction into its components
    Example input: 
    instruction = "CADD"
    operand = "A, BUFFER, Z"
    Returns: (opcode, register, address, condition)
    """
    opcode = instruction
    parts = operand.replace(',', ' ').split()
    
    # Default values
    register = parts[0] if len(parts) > 0 else 'A'
    address = parts[1] if len(parts) > 1 else '0'
    condition = parts[2] if len(parts) > 2 else 'Z'
    
    return opcode, register, address, condition

def handle_4f_instruction(instruction, operand, symbol_table):
    opcode, register, address, condition = parse_4f_instruction(instruction, operand)
    
    # Look up address in symbol table if it's a symbol
    if address in symbol_table:
        address = symbol_table[address]
    
    # Get opcode value from FORMAT_4F_OPCODES
    opcode_value = FORMAT_4F_OPCODES.get(opcode, '000000')
    
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
                    value = parts[1]
                    address = parts[3]
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
    if instruction.split()[0] in FORMAT_4F_OPCODES:
        return '4F'
    return 3

def parse_operand(operand):
    if not operand:
        return None, None
    
    if operand.startswith('#'):
        return 'immediate', operand[1:]
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
    else:  # simple or indexed
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
    
    pc = int(current_location, 16) + 3
    disp = target_address - pc
    
    if -2048 <= disp <= 2047:
        return disp, 0, 1, 0  # PC relative
    elif base_register and 0 <= (target_address - int(base_register, 16)) <= 4095:
        return target_address - int(base_register, 16), 1, 0, 0  # Base relative
    else:
        return target_address & 0xFFF, 0, 0, 0  # Direct addressing

def generate_object_code(location, instruction, operand, symbol_table, literal_table, base_register=None):
    is_format_4 = instruction.startswith('+')
    if is_format_4:
        instruction = instruction[1:]

    if instruction == 'RSUB':
        return '4F0000'

    if instruction not in OPCODE_TABLE and instruction not in FORMAT_4F_OPCODES:
        return None

    # Handle Format 4F instructions
    if instruction in FORMAT_4F_OPCODES:
        return handle_4f_instruction(instruction, operand, symbol_table)

    opcode = OPCODE_TABLE[instruction]
    format_type = get_instruction_format(instruction, opcode)
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
            return format(opcode_val, '02X') + str(r1_val) + str(r2_val)
        else:
            r1_val = REGISTERS[operand] if operand in REGISTERS else operand[-1]
            return format(opcode_val, '02X') + str(r1_val) + '0'

    mode, operand_value = parse_operand(operand)
    n, i = calculate_flags(mode)
    x = 1 if mode == 'indexed' else 0

    opcode_val = get_opcode_value(opcode)
    opcode_ni = (opcode_val << 2) | (n << 1) | i

    target_address = 0
    if operand_value:
        if mode == 'immediate':
            if operand_value.isdigit() or (operand_value.startswith('-') and operand_value[1:].isdigit()):
                return format(opcode_ni, '02X') + '0' + format(int(operand_value) & 0xFFF, '03X')
            elif operand_value in symbol_table:
                target_address = int(symbol_table[operand_value], 16)
        else:
            if operand_value.startswith('='):
                if operand_value in literal_table:
                    literal_address, _ = literal_table[operand_value]
                    target_address = int(literal_address, 16)
            elif operand_value in symbol_table:
                target_address = int(symbol_table[operand_value], 16)

    disp, b, p, e = calculate_displacement(target_address, location, format_type, base_register)
    flags = (x << 3) | (b << 2) | (p << 1) | e

    if format_type == 3:
        return format(opcode_ni, '02X') + format(flags, '01X') + format(disp & 0xFFF, '03X')
    else:  # Format 4
        return format(opcode_ni, '02X') + format(flags, '01X') + format(target_address & 0xFFFFF, '05X')

def process_intermediate_file(intermediate_file, symbol_table, literal_table, output_file):
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
        elif instruction in OPCODE_TABLE or instruction in FORMAT_4F_OPCODES or (instruction.startswith('+') and instruction[1:] in OPCODE_TABLE):
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

def pass2(intermediate_file, symb_table_file, output_file):
    """
    Process intermediate file and symbol table to generate object code
    """
    try:
        # Load symbol table and process intermediate file
        symbol_table = load_symbol_table(symb_table_file)  # Pass the file path
        literal_table = load_literal_table(symb_table_file)  # Pass the file path
        
        with open(output_file, 'w') as out:
            # Process intermediate file and generate object code
            process_intermediate_file(intermediate_file, symbol_table, literal_table, output_file)
            
    except Exception as e:
        raise Exception(f"Pass 2 error: {e}")

if __name__ == "__main__":
    process_intermediate_file()