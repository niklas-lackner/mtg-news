#!/usr/bin/env python3
import subprocess
import os
import sys
import datetime

# Update this path to point to your local Git repository
REPO_PATH = r'C:\Users\lackn\Desktop\my-mtg-project\mtg-news'

# Change the working directory to the repository
os.chdir(REPO_PATH)

def run_command(cmd):
    """
    Helper function to run shell commands and capture output.
    """
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print("Error executing command:", ' '.join(cmd))
        print(e.stderr)
        sys.exit(1)

def main():
    # Stage all changes (this includes new, modified, or deleted log files)
    run_command(['git', 'add', '.'])

    # Check if there are any changes to commit
    status_output = run_command(['git', 'status', '--porcelain'])
    if not status_output.strip():
        print("No changes to commit.")
        return

    # Create a commit message with the current timestamp
    commit_message = "Automated log update: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_command(['git', 'commit', '-m', commit_message])
    run_command(['git', 'push'])
    print("Log files pushed to GitHub successfully.")

if __name__ == '__main__':
    main()
