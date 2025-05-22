import os


def append_to_log_file(file_path: str, line_content: str):
    """
    Appends a given string as a new line to a specified text file.

    Creates the file if it does not exist. Each call adds the content
    as a new line at the end, preserving previous content.

    Args:
        file_path: The path to the text file where logs/descriptions will be written.
        line_content: The string content to write as a single line.
    """
    try:
        # Open the file in append mode ('a'). If the file doesn't exist,
        # it will be created. The 'with' statement ensures the file is
        # automatically closed even if errors occur.
        with open(file_path, 'a', encoding='utf-8') as f:
            # Write the content followed by a newline character to ensure
            # subsequent writes start on a new line.
            f.write(line_content + '\n')
        # Optional: print confirmation to console (can be removed in production)
        # print(f"Successfully appended log: '{line_content}' to {file_path}")
    except IOError as e:
        # Catch potential input/output errors (e.g., permission denied, disk full)
        print(f"Error writing to log file {file_path}: {e}")
    except Exception as e:
        # Catch any other unexpected errors during file writing
        print(f"An unexpected error occurred while logging: {e}")
