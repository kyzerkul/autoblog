#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Startup script with strict ASCII encoding settings
"""
import os
import sys
import subprocess

# Force ASCII encoding for environment variables
os.environ["PYTHONIOENCODING"] = "ascii"
os.environ["LANG"] = "C"
os.environ["LC_ALL"] = "C"

# Set a clean environment for the subprocess
my_env = os.environ.copy()
for key in ["PYTHONIOENCODING", "LANG", "LC_ALL"]:
    my_env[key] = os.environ[key]

# Run app.py as a subprocess with the clean environment
if __name__ == "__main__":
    print("Starting application with ASCII encoding...")
    process = subprocess.Popen(
        [sys.executable, "app.py"],
        env=my_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    
    # Print output in real-time
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
    
    # Print any errors
    stderr = process.stderr.read()
    if stderr:
        print("Errors:", stderr)
    
    sys.exit(process.poll())
