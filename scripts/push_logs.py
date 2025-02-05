#!/usr/bin/env python3
import os
import sys
import subprocess
import datetime
import json
import re

# --- Configuration ---

# Local Git repository root (the folder that contains the .git folder)
REPO_PATH = r'C:\Users\lackn\Desktop\my-mtg-project\mtg-news'

# File where parsed MTG data will be stored (you can change the file name or location)
JSON_OUTPUT = os.path.join(REPO_PATH, 'mtg_data.json')

# Directory where MTG Arena log files are located
MTG_LOG_SOURCE = r'C:\Users\lackn\AppData\LocalLow\Wizards Of The Coast\MTGA'

# --- End Configuration ---

def run_command(cmd):
    """Helper function to run shell commands and capture output."""
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print("Error executing command:", ' '.join(cmd))
        print(e.stderr)
        sys.exit(1)

def parse_mtg_logs():
    """
    Parse MTG Arena log files and extract useful data.
    In this example, we search for lines with "MatchResult:" and try to capture a result.
    Adjust the regex patterns as needed for your log file structure.
    """
    parsed_data = {
        "games": [],
        "last_updated": datetime.datetime.now().isoformat()
    }
    
    if not os.path.exists(MTG_LOG_SOURCE):
        print("MTG log source folder does not exist:", MTG_LOG_SOURCE)
        return parsed_data

    # Loop through all files in the log source directory
    for filename in os.listdir(MTG_LOG_SOURCE):
        if filename.lower().endswith(".log"):  # Adjust if your logs have a different extension
            filepath = os.path.join(MTG_LOG_SOURCE, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        # Example: Look for lines that contain "MatchResult:" and capture the result word.
                        # You may want to adjust the regex to match your log format.
                        match = re.search(r'MatchResult:\s*(\w+)', line)
                        if match:
                            result = match.group(1)
                            # Try to extract a timestamp from the start of the line (format "YYYY-MM-DD HH:MM:SS")
                            ts_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                            timestamp = ts_match.group(1) if ts_match else "unknown"
                            parsed_data["games"].append({
                                "timestamp": timestamp,
                                "result": result,
                                "source_file": filename
                            })
            except Exception as e:
                print(f"Error processing file {filepath}: {e}")
    
    print(f"Parsed {len(parsed_data['games'])} game entries from log files.")
    return parsed_data

def write_json_data(data, output_file):
    """Write the parsed data to a JSON file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Written parsed data to {output_file}")
    except Exception as e:
        print(f"Error writing JSON data: {e}")

def main():
    # Change directory to the repository root so that git commands work correctly.
    os.chdir(REPO_PATH)

    # Parse the MTG logs and write the useful info to a JSON file.
    parsed_data = parse_mtg_logs()
    write_json_data(parsed_data, JSON_OUTPUT)

    # Stage all changes (this includes our updated JSON file)
    run_command(['git', 'add', '.'])

    # Check if there are any changes to commit.
    status_output = run_command(['git', 'status', '--porcelain'])
    if not status_output.strip():
        print("No changes to commit.")
        return

    # Create a commit message with the current timestamp.
    commit_message = "Automated log update: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_command(['git', 'commit', '-m', commit_message])
    
    # (Optional) Pull remote changes first to ensure your branch is up-to-date.
    print("Pulling remote changes...")
    run_command(['git', 'pull', '--rebase', 'origin', 'main'])
    
    # Push the commit to GitHub.
    run_command(['git', 'push'])
    print("Log data pushed to GitHub successfully.")

if __name__ == '__main__':
    main()
