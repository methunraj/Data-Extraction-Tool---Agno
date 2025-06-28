#!/usr/bin/env python3
"""
Simple server management script for the FastAPI backend.
"""

import os
import sys
import signal
import subprocess
import time
import argparse

class SimpleServerManager:
    def __init__(self, port=None):
        self.port = port or int(os.getenv("PORT", 8000))
        self.pid_file = f"/tmp/intelliextract_backend_{port}.pid"
        
    def find_process_on_port(self):
        """Find process IDs using the port."""
        try:
            # Use lsof to find processes on the port
            result = subprocess.run(
                ['lsof', '-t', f'-i:{self.port}'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = list(set(result.stdout.strip().split('\n')))
                return [int(pid) for pid in pids if pid]
            return []
        except Exception as e:
            print(f"Error finding processes: {e}")
            return []
    
    def stop_server(self, force=False):
        """Stop the FastAPI server."""
        print(f"🛑 Stopping server on port {self.port}...")
        
        # Get all PIDs using the port
        pids = self.find_process_on_port()
        
        if not pids:
            print(f"✅ No server running on port {self.port}")
            # Clean up PID file if exists
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            return
        
        print(f"Found {len(pids)} process(es) on port {self.port}: {pids}")
        
        # Try graceful shutdown first
        for pid in pids:
            try:
                print(f"  Sending SIGTERM to PID {pid}...")
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                print(f"  Process {pid} already gone")
            except PermissionError:
                print(f"  Permission denied for PID {pid}")
        
        # Wait a bit
        time.sleep(2)
        
        # Check if processes are still running
        remaining_pids = self.find_process_on_port()
        
        if remaining_pids and (force or len(remaining_pids) > 0):
            print(f"⚠️  {len(remaining_pids)} process(es) still running, force killing...")
            for pid in remaining_pids:
                try:
                    print(f"  Sending SIGKILL to PID {pid}...")
                    os.kill(pid, signal.SIGKILL)
                except:
                    pass
            time.sleep(1)
        
        # Final check
        final_pids = self.find_process_on_port()
        if final_pids:
            print(f"❌ Failed to stop all processes. Still running: {final_pids}")
        else:
            print(f"✅ Port {self.port} is now free")
        
        # Clean up PID file
        if os.path.exists(self.pid_file):
            os.remove(self.pid_file)
    
    def start_server(self, reload=True, background=False):
        """Start the FastAPI server."""
        # First ensure no server is running
        existing_pids = self.find_process_on_port()
        if existing_pids:
            print(f"⚠️  Server already running on port {self.port} (PIDs: {existing_pids})")
            print("Use 'python manage.py stop' first or 'python manage.py restart'")
            return
        
        print(f"🚀 Starting FastAPI server on port {self.port}...")
        
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(self.port)
        ]
        
        if reload:
            cmd.append("--reload")
        
        if background:
            # Start in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
            
            # Save PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            print(f"✅ Server started in background with PID {process.pid}")
            print(f"   Access at: http://localhost:{self.port}")
            print(f"   Logs: Check terminal where uvicorn is running")
            print(f"   Stop with: python manage.py stop")
        else:
            # Start in foreground
            print(f"✅ Server starting at http://localhost:{self.port}")
            print("   Press Ctrl+C to stop\n")
            
            try:
                process = subprocess.Popen(cmd)
                with open(self.pid_file, 'w') as f:
                    f.write(str(process.pid))
                process.wait()
            except KeyboardInterrupt:
                print("\n\n🛑 Shutting down server...")
                self.stop_server()
                sys.exit(0)
    
    def status(self):
        """Check server status."""
        pids = self.find_process_on_port()
        
        if pids:
            print(f"✅ Server is running on port {self.port}")
            print(f"   PIDs: {pids}")
            
            # Try to get more info about the processes
            for pid in pids:
                try:
                    result = subprocess.run(
                        ['ps', '-p', str(pid), '-o', 'pid,ppid,user,command'],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            print(f"   {lines[1]}")
                except:
                    pass
        else:
            print(f"❌ No server running on port {self.port}")
        
        if os.path.exists(self.pid_file):
            with open(self.pid_file, 'r') as f:
                saved_pid = f.read().strip()
                if saved_pid not in [str(p) for p in pids]:
                    print(f"⚠️  Stale PID file found: {saved_pid}")

def main():
    parser = argparse.ArgumentParser(
        description='IntelliExtract Backend Server Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage.py start              # Start server with auto-reload
  python manage.py start --background # Start server in background
  python manage.py stop               # Stop server
  python manage.py restart            # Restart server
  python manage.py status             # Check server status
        """
    )
    
    parser.add_argument('command', 
                        choices=['start', 'stop', 'restart', 'status', 'kill'],
                        help='Command to execute')
    parser.add_argument('--port', type=int, default=8000,
                        help='Port number (default: 8000)')
    parser.add_argument('--no-reload', action='store_true',
                        help='Disable auto-reload')
    parser.add_argument('--background', '-b', action='store_true',
                        help='Run server in background')
    
    args = parser.parse_args()
    
    manager = SimpleServerManager(port=args.port)
    
    if args.command == 'start':
        manager.start_server(reload=not args.no_reload, background=args.background)
    elif args.command == 'stop':
        manager.stop_server()
    elif args.command == 'kill':
        manager.stop_server(force=True)
    elif args.command == 'restart':
        manager.stop_server()
        time.sleep(1)
        manager.start_server(reload=not args.no_reload, background=args.background)
    elif args.command == 'status':
        manager.status()

if __name__ == '__main__':
    main()