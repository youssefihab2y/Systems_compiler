import os
from pass1.pass1 import pass1

def main():
    # Define file paths
    input_file = "input/input.txt"                # Input assembly file
    output_dir = "Output"                         # Directory for output files

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Define output files
    intermediate_file = os.path.join(output_dir, "intermediate.txt")
    symb_table_file = os.path.join(output_dir, "symbTable.txt")
    lc_file = os.path.join(output_dir, "out_pass1.txt")

    # Run Pass 1
    print("Running Pass 1...")
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

if __name__ == "__main__":
    main()