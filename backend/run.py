import uvicorn 
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_backend_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(Path(_backend_dir) / ".env")
sys.path.insert(0, _backend_dir)  # Add the current directory to the system path


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Neural Style Transfer API Server",
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python run.py                    # Development (reload open, port 8000)
  python run.py --prod             # Production modu (reload off)
  python run.py --port 9000        # run on port 9000
  python run.py --host 127.0.0.1   # Only localhost
"""
    )

    parser.add_argument(
        "--host",
        type=str,
        default=os.getenv("HOST", "0.0.0.0"),
        help= "Host to bind the server to (default: 0.0.0.0 - accessible from any network interface)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port number to listen on (default: 8000)"
    )

    parser.add_argument(
        "--reload",
        dest="reload",
        action="store_true",
        default=True,
        help="restart the server when code changes (development mode, default: on)"
    )
    
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="disable automatic restart (production mode)"
    )
    
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Production mode (shortcut for reload=False, host=0.0.0.0, port=8000)"
    )

    return parser.parse_args()

def main():

    args = parse_arguments()

    if args.prod:
        args.reload = False
        print("Running in production mode")
    else:
        print("Running in development mode")

    #Sunucu başlatma bilgilerini göstermek için:

    print("=" * 50)
    print("Backend Server for Neural Style Transfer")
    print("=" * 50)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Auto-reload: {'Open' if args.reload else 'Closed'}")
    print("=" * 50)
    print(f"API Documentation: http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/docs")
    print(f"Health Check: http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}/health")
    print("=" * 50)
    print("\nServer starting... (Press Ctrl+C to stop)\n")


    # Uvicorn sunucusunu başlat
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
        access_log=True,
    )

# run.py
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0", 
        port=8000,
        reload=False  
    )