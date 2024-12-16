import os
from pass1.pass1 import pass1

def run_pass1(input_file, output_dir):
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Define output files
    intermediate_file = os.path.join(output_dir, "intermediate.txt")
    symb_table_file = os.path.join(output_dir, "symbTable.txt")
    lc_file = os.path.join(output_dir, "out_pass1.txt")

    # Run Pass 1
    print(f"\nRunning Pass 1 for {input_file}...")
    try:
        pass1(
            input_file=input_file,
            intermediate_file=intermediate_file,
            symb_table_file=symb_table_file,
            lc_file=lc_file
        )
        print("Pass 1 completed successfully.")
        print("Generated files:")
        print(f"- Intermediate file: {intermediate_file}")
        print(f"- Symbol table file: {symb_table_file}")
        print(f"- Location counter file: {lc_file}")
    except Exception as e:
        print(f"Error during Pass 1: {e}")

def main():
    # Define file paths
    input_files = [
        "input/input.txt",    # Original input file
        "input/input2.txt"    # New input file
    ]
    output_dir = "Output"     # Directory for output files

    # Process each input file
    for input_file in input_files:
        if os.path.exists(input_file):
            # Create specific output directory for each input
            file_name = os.path.splitext(os.path.basename(input_file))[0]
            specific_output_dir = os.path.join(output_dir, file_name)
            run_pass1(input_file, specific_output_dir)
        else:
            print(f"Input file not found: {input_file}")

if __name__ == "__main__":
    main()