import os
from pass1.pass1 import pass1
from pass2.pass2 import pass2

def run_pass1(input_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    intermediate_file = os.path.join(output_dir, "intermediate.txt")
    symb_table_file = os.path.join(output_dir, "symbTable.txt")
    lc_file = os.path.join(output_dir, "out_pass1.txt")

    print(f"\nRunning Pass 1 for {input_file}...")
    try:
        pass1(input_file, intermediate_file, symb_table_file, lc_file)
        print("Pass 1 completed successfully.")
        return intermediate_file, symb_table_file  # Return files for pass2
    except Exception as e:
        print(f"Error during Pass 1: {e}")
        return None, None

def run_pass2(intermediate_file, symb_table_file, output_dir):
    print("\nRunning Pass 2...")
    try:
        out_file = os.path.join(output_dir, "out_pass2.txt")
        pass2(intermediate_file, symb_table_file, out_file)
        print("Pass 2 completed successfully.")
        print(f"Generated object code file: {out_file}")
        return out_file
    except Exception as e:
        print(f"Error during Pass 2: {e}")
        return None


def main():
    input_files = [
        "input/input.txt",
        "input/input2.txt",
        "input/input3.txt"
    ]
    output_dir = "Output"

    for input_file in input_files:
        if os.path.exists(input_file):
            file_name = os.path.splitext(os.path.basename(input_file))[0]
            specific_output_dir = os.path.join(output_dir, file_name)
            
            # Run Pass 1
            intermediate_file, symb_table_file = run_pass1(input_file, specific_output_dir)
            
            # Run Pass 2 if Pass 1 was successful
            if intermediate_file and symb_table_file:
                pass2_output = run_pass2(intermediate_file, symb_table_file, specific_output_dir)
    
        else:
            print(f"Input file not found: {input_file}")

if __name__ == "__main__":
    main()