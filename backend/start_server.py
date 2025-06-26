#!/usr/bin/env python3
"""
Development server startup script for IntelliExtract backend
"""

import os
import sys
import subprocess
from pathlib import Path

def check_env_file():
    """Check if global .env file exists and has required variables"""
    # Look for global .env file in project root
    script_dir = Path(__file__).parent.absolute()
    global_env_file = script_dir.parent / ".env"
    
    if not global_env_file.exists():
        print("⚠️  Global .env file not found!")
        print("🔧 Please run ./setup-env.sh from the project root")
        print(f"📍 Expected location: {global_env_file}")
        return False
    
    # Check if GOOGLE_API_KEY is set
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=global_env_file)
    
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ GOOGLE_API_KEY not set in global .env file!")
        print("🔧 Please add your Google API key to the global .env file")
        return False
    
    print("✅ Global environment configuration looks good")
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import agno
        import pandas
        print("✅ Core dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("📦 Please install dependencies:")
        print("   pip install -r requirements.txt")
        return False

def start_server(host="127.0.0.1", port=8000, reload=True):
    """Start the FastAPI server"""
    print(f"🚀 Starting IntelliExtract backend server...")
    print(f"📍 URL: http://{host}:{port}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print("💡 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Change to the script directory before starting the server
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app.main:app",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

def main():
    """Main startup function"""
    print("🔧 IntelliExtract Backend - Development Server")
    print("=" * 50)
    
    # Check environment
    if not check_env_file():
        return
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Parse command line arguments
    host = "127.0.0.1"
    port = 8000
    reload = True
    
    if len(sys.argv) > 1:
        if "--host" in sys.argv:
            idx = sys.argv.index("--host")
            if idx + 1 < len(sys.argv):
                host = sys.argv[idx + 1]
        
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            if idx + 1 < len(sys.argv):
                port = int(sys.argv[idx + 1])
        
        if "--no-reload" in sys.argv:
            reload = False
    
    # Start the server
    start_server(host, port, reload)

if __name__ == "__main__":
    main()