#!/usr/bin/env python3
import os
import sys
import subprocess
import datetime
import json
import re

# --- Configuration ---
REPO_PATH = r'C:\Users\lackn\Desktop\my-mtg-project\mtg-news'
JSON_OUTPUT = os.path.join(REPO_PATH, 'mtg_data.json')
MTG_LOG_SOURCE = r'C:\Users\lackn\AppData\LocalLow\Wizards Of The Coast\MTGA'
MATCH_RESULT_REGEX = re.compile(r'MatchResult:\s*(\w+)')
TIMESTAMP_REGEX = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
# --- End Configuration ---

def run_command(cmd):
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print("Error executing command:", ' '.join(cmd))
        print(e.stderr)
        sys.exit(1)

def parse_mtg_logs():
    parsed_data = {
        "games": [],
        "last_updated": datetime.datetime.now().isoformat()
    }
    if not os.path.exists(MTG_LOG_SOURCE):
        print("MTG log source folder does not exist:", MTG_LOG_SOURCE)
        return parsed_data

    for filename in os.listdir(MTG_LOG_SOURCE):
        if filename.lower().endswith(".log"):
            filepath = os.path.join(MTG_LOG_SOURCE, filename)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        ts_match = TIMESTAMP_REGEX.match(line)
                        timestamp = ts_match.group(1) if ts_match else "unknown"
                        match = MATCH_RESULT_REGEX.search(line)
                        if match:
                            result = match.group(1)
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
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Written parsed data to {output_file}")
    except Exception as e:
        print(f"Error writing JSON data: {e}")

def main():
    os.chdir(REPO_PATH)
    parsed_data = parse_mtg_logs()
    write_json_data(parsed_data, JSON_OUTPUT)
    run_command(['git', 'add', '.'])
    status_output = run_command(['git', 'status', '--porcelain'])
    if not status_output.strip():
        print("No changes to commit.")
        return
    commit_message = "Automated log update: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_command(['git', 'commit', '-m', commit_message])
    print("Pulling remote changes...")
    run_command(['git', 'pull', '--rebase', 'origin', 'main'])
    run_command(['git', 'push'])
    print("Log data pushed to GitHub successfully.")

if __name__ == '__main__':
    main()
