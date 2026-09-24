"""
Single-command launcher for Song Chord Analyzer.
Starts the FastAPI server with CUDA hardware acceleration.
Supports command-line arguments: --port, --host, --no-browser.
"""

import sys
import os
import argparse
import webbrowser
import threading
import time
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

def open_browser(port: int):
    time.sleep(1.5)
    print(f"\n[Launcher] Opening Song Chord Analyzer in browser: http://127.0.0.1:{port}\n", flush=True)
    webbrowser.open(f"http://127.0.0.1:{port}")

def main():
    parser = argparse.ArgumentParser(description="Song Chord Analyzer Backend Server")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SONG_CHORD_ANALYZER_PORT", 8000)),
        help="Port to run FastAPI server on (default 8000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("SONG_CHORD_ANALYZER_HOST", "127.0.0.1"),
        help="Host address to bind (default 127.0.0.1)"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        default=bool(os.environ.get("SONG_CHORD_ANALYZER_NO_BROWSER", False)),
        help="Do not open browser automatically (used by Electron desktop shell)"
    )

    args = parser.parse_args()

    print("=" * 60, flush=True)
    print("      SONG CHORD ANALYZER — Starting Application Server", flush=True)
    print(f"      Host: {args.host} | Port: {args.port}", flush=True)
    print("=" * 60, flush=True)

    if not args.no_browser:
        threading.Thread(target=open_browser, args=(args.port,), daemon=True).start()

    import uvicorn
    from backend.main import app

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )

if __name__ == "__main__":
    main()
