# combine_code.py
import os
import sys

# --- Configuration ---
# The directory containing your source (.py) files
# Assumes 'src' is in the same directory as this script
SOURCE_DIRECTORY = 'src_GM'
# The name of the output file where combined code will be saved
OUTPUT_FILENAME = 'combined_code.txt'
# --- End Configuration ---

def combine_py_files(src_dir, output_file):
    """
    Walks through src_dir, finds all .py files, and combines their content
    into output_file.
    """
    combined_code = []
    script_dir = os.path.dirname(os.path.abspath(__file__)) # Get script's directory
    full_src_path = os.path.join(script_dir, src_dir)

    print(f"Looking for .py files in: {full_src_path}")

    if not os.path.isdir(full_src_path):
        print(f"Error: Source directory '{full_src_path}' not found.")
        print("Make sure the 'src' folder exists in the same directory as this script.")
        sys.exit(1) # Exit with an error code

    # Walk through the source directory
    for root, dirs, files in os.walk(full_src_path):
        # Sort files for consistent order (optional but nice)
        files.sort()
        for filename in files:
            if filename.endswith(".py"):
                relative_path = os.path.relpath(os.path.join(root, filename), script_dir)
                full_filepath = os.path.join(root, filename)

                print(f"  Adding: {relative_path}")

                # Add a header indicating the file path
                combined_code.append(f"\n{'=' * 30} START FILE: {relative_path} {'=' * 30}\n")

                try:
                    with open(full_filepath, 'r', encoding='utf-8') as infile:
                        combined_code.append(infile.read())
                except Exception as e:
                    error_message = f"!!! ERROR READING FILE {relative_path}: {e} !!!"
                    print(f"    WARNING: {error_message}")
                    combined_code.append(f"\n{error_message}\n")

                # Add a footer
                combined_code.append(f"\n{'=' * 30} END FILE: {relative_path} {'=' * 30}\n")

    output_filepath = os.path.join(script_dir, output_file)

    if not combined_code:
        print(f"Warning: No '.py' files found in '{full_src_path}'. Output file will be empty.")

    # Write the combined content to the output file
    try:
        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            outfile.write("\n".join(combined_code))
        print(f"\nSuccessfully combined code into: {output_filepath}")
    except Exception as e:
        print(f"\nError writing to output file '{output_filepath}': {e}")
        sys.exit(1)

if __name__ == "__main__":
    combine_py_files(SOURCE_DIRECTORY, OUTPUT_FILENAME)