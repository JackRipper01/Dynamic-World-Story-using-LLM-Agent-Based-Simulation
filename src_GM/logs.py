import os

# Initialize a function attribute to track if the file has been written to
# in the current execution. We start assuming it hasn't been.


def append_to_log_file(file_path: str, line_content: str):
    """
    Writes a string as a new line to a specified text file.
    Clears the file on the first call within a program execution.
    Appends on subsequent calls.

    Creates the file if it does not exist.

    Args:
        file_path: The path to the text file where logs/descriptions will be written.
        line_content: The string content to write as a single line.
    """
    try:
        # Check if this is the very first call in this execution
        # We use the function attribute _first_call_done
        if not append_to_log_file._first_call_done:
            # If it's the first call, open in write mode ('w').
            # This mode clears the file if it exists, or creates it if it doesn't.
            # Optional debug print
            print(f"Clearing and writing first log entry to {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(line_content + '\n')

            # Now that the first write (and clearing) is done, set the flag to True
            append_to_log_file._first_call_done = True
            # NOTE: This flag is global for the function. If you were logging
            # to *multiple* different files and needed each one cleared on *its*
            # first call, you'd need a more complex mechanism (e.g., a dictionary
            # mapping file_path to a boolean flag). For a single main log file,
            # this approach works fine.

        else:
            # For subsequent calls in the same execution, open in append mode ('a')
            # This adds new content to the end of the existing file.
            # print(f"Appending log entry to {file_path}") # Optional debug print
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(line_content + '\n')

        # Optional: print content logged for immediate console feedback
        # print(f"Logged: {line_content}")

    except IOError as e:
        # Catch potential input/output errors (e.g., permission denied, disk full)
        print(f"Error writing to log file {file_path}: {e}")
    except Exception as e:
        # Catch any other unexpected errors during file writing
        print(f"An unexpected error occurred while logging: {e}")

# --- How to use this updated function ---
# You would use it exactly the same way as before. The internal logic
# handles the clearing on the first call automatically.

# Example Usage:
# log_file = "simulation_output.txt"

# # First call - Clears the file if it exists, writes "First line log"
# append_to_log_file(log_file, "First line log")

# # Second call - Appends "Second line log" to the file
# append_to_log_file(log_file, "Second line log")

# # Third call - Appends "Third line log" to the file
# append_to_log_file(log_file, "Third line log")

# If you run the script again, the *next* time append_to_log_file is called,
# _first_call_done will be reset to False, and the file will be cleared again
# before the new "First line log" (or whatever the first content is) is written.


append_to_log_file._first_call_done = False
