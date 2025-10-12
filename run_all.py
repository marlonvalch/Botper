#!/usr/bin/env python3
"""
Botper startup script - now redirects to main.py with smart startup
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    print("Botper Startup")
    print("=" * 30)
    print("Starting integrated bot with smart port management...")
    print()
    
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Run main.py from botper directory
    try:
        result = subprocess.run([
            sys.executable, 
            'botper/main.py'
        ], cwd=project_root)
        return result.returncode
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you're in the correct directory and botper/main.py exists")
        return 1

if __name__ == "__main__":
    sys.exit(main())