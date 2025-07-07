#!/usr/bin/env python3
"""
Helper script to kill any remaining voice demo processes
"""

import os
import subprocess
import sys

def kill_voice_demos():
    """Kill any running voice demo processes"""
    print("🔍 Looking for voice demo processes...")
    
    try:
        # Find all python processes with voice_demo in the name
        result = subprocess.run(
            ['ps', 'aux'], 
            capture_output=True, 
            text=True
        )
        
        killed_count = 0
        
        for line in result.stdout.split('\n'):
            if 'python' in line and 'voice_demo' in line:
                parts = line.split()
                if len(parts) >= 2:
                    pid = parts[1]
                    process_name = ' '.join(parts[10:])
                    
                    print(f"🎯 Found: PID {pid} - {process_name}")
                    
                    try:
                        # Kill the process
                        os.kill(int(pid), 9)  # SIGKILL
                        print(f"✅ Killed process {pid}")
                        killed_count += 1
                    except ProcessLookupError:
                        print(f"⚠️  Process {pid} already terminated")
                    except PermissionError:
                        print(f"❌ Permission denied for process {pid}")
                    except Exception as e:
                        print(f"❌ Error killing {pid}: {e}")
        
        if killed_count == 0:
            print("✅ No voice demo processes found")
        else:
            print(f"✅ Killed {killed_count} voice demo processes")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    kill_voice_demos() 