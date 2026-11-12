#!/usr/bin/env python3
"""
Synfig MCP Website Preview Server
Launches a lightweight local HTTP server and opens the website in default browser.
"""

import http.server
import os
import socketserver
import sys
import webbrowser
from pathlib import Path

PORT = 8000
DIRECTORY = Path(__file__).resolve().parent.parent / "website"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

def main():
    if not DIRECTORY.exists():
        print(f"Error: Website directory not found at {DIRECTORY}")
        sys.exit(1)

    os.chdir(DIRECTORY)
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/"
        print("=" * 60)
        print("  Synfig MCP — Official Website Preview Server")
        print(f"  Serving at: {url}")
        print(f"  Root dir:   {DIRECTORY}")
        print("  Press Ctrl+C to stop.")
        print("=" * 60)
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            httpd.shutdown()

if __name__ == "__main__":
    main()
