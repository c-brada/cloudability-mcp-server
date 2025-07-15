#!/usr/bin/env python3
"""
Script to run the Cloudability MCP server locally.

This script can be used to start the MCP server for local development and testing.
"""

import sys
import os
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from main import mcp

if __name__ == "__main__":
    print("Starting Cloudability MCP Server...")
    print("Press Ctrl+C to stop the server")
    try:
        mcp.run()
    except KeyboardInterrupt:
        print("\nServer stopped.")
