#!/usr/bin/env python3
"""
Enhanced Anki integration script that implements a complete workflow for:

• Checking operating system type  
• Verifying if Anki is running  
• Bringing the Anki window to the front  
• Reading note IDs from standard input (STDIN) ONLY  
• Populating the browser with the provided note-ID query via AnkiConnect

Usage:
    This script is invoked by `search_essential_logic/core.py`, which sends a JSON
    payload to STDIN, e.g.:

    {"formatted_nids": "nid:123,456,789"}

No command-line arguments are supported anymore.
"""

import subprocess
import platform
import requests
import sys
import json
from typing import Dict, Optional
from loguru import logger
import ctypes

# Remove any default loguru sinks (they will be configured by the parent process)
logger.remove()
# Add a stderr sink that only emits ERROR / CRITICAL messages
logger.add(
    sys.stderr,
    level="ERROR",                              # only show errors
    format="{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {message}",
    enqueue=True,
)

# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
def is_program_running(program_name: str) -> bool:
    """
    Check if a program is running on macOS or Windows.

    Args:
        program_name (str): Name of the program to check (e.g., "anki").

    Returns:
        bool: True if the program is running, False otherwise.

    Raises:
        Exception: If there's an error checking the program status.
    """
    system = platform.system()
    logger.debug(f"Checking if {program_name} is running on {system}")
    try:
        if system == "Darwin":  # macOS
            res = subprocess.run(
                ["pgrep", "-x", program_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            return res.returncode == 0
        elif system == "Windows":
            res = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {program_name}.exe"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return f"{program_name}.exe" in res.stdout
        else:
            logger.error(f"Unsupported operating system: {system}")
            return False
    except Exception as exc:
        logger.error(f"Error checking if {program_name} is running: {exc}")
        return False


def bring_anki_to_front() -> bool:
    """
    Bring the Anki window to the foreground.

    Returns:
        bool: True if successfully brought Anki to front, False otherwise.

    Raises:
        Exception: If there's an error bringing the window to front.
    """
    system = platform.system()
    logger.debug(f"Attempting to bring Anki to front on {system}")
    try:
        if system == "Darwin":
            cmd = ["osascript", "-e", 'tell application "Anki" to activate']
            return subprocess.run(cmd, capture_output=True, text=True).returncode == 0
        elif system == "Windows":
            logger.info("Attempting to bring Anki to front using Windows commands …")
            cmd = [
                "powershell",
                """
                Add-Type @"
                    using System;
                    using System.Runtime.InteropServices;
                    public class Win32 {
                        [DllImport("user32.dll")]
                        public static extern bool SetForegroundWindow(IntPtr hWnd);
                        [DllImport("user32.dll")]
                        public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
                    }
"@
                $hwnd = [Win32]::FindWindow($null, "Anki")
                [Win32]::SetForegroundWindow($hwnd)
            """,
            ]
            return subprocess.run(cmd, capture_output=True, text=True).returncode == 0
        else:
            logger.error(f"Unsupported operating system for window focus: {system}")
            return False
    except Exception as exc:
        logger.error(f"Error bringing Anki to front: {exc}")
        return False


def populate_anki_browser(query: str) -> bool:
    """
    Populate Anki's browser with the given search query using AnkiConnect.

    Args:
        query (str): The search query to send to Anki browser.

    Returns:
        bool: True if successfully populated the browser, False otherwise.

    Raises:
        requests.exceptions.RequestException: If communication with AnkiConnect fails.
        Exception: For any other unexpected errors.
    """
    if not query:
        logger.warning("Empty query provided to populate_anki_browser")
        return False

    url = "http://localhost:8765"
    payload = {"action": "guiBrowse", "version": 6, "params": {"query": query}}

    try:
        logger.info(f"Sending request to AnkiConnect: {payload}")
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        if result.get("error"):
            logger.error(f"AnkiConnect returned error: {result['error']}")
            return False
        logger.info("Successfully populated Anki browser")
        return True
    except requests.exceptions.RequestException as exc:
        logger.error(f"Failed to communicate with AnkiConnect: {exc}")
        return False
    except Exception as exc:
        logger.error(f"Unexpected error in populate_anki_browser: {exc}")
        return False


def read_input_data() -> Dict:
    """
    Read and parse JSON input data from STDIN.

    Returns:
        Dict: A dictionary containing the parsed JSON data with at least a 
            'formatted_nids' key. Returns {'formatted_nids': ''} if input is invalid.

    Raises:
        json.JSONDecodeError: If the input is not valid JSON.
        Exception: For any other unexpected errors.
    """
    try:
        raw = sys.stdin.read()
        logger.info(f"Raw input data received: {raw}")
        if not raw:
            logger.error("No input received on STDIN")
            return {"formatted_nids": ""}
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"Failed to parse JSON input: {exc}")
        return {"formatted_nids": ""}
    except Exception as exc:
        logger.error(f"Unexpected error reading input: {exc}")
        return {"formatted_nids": ""}


def validate_nids_query(query: str) -> bool:
    """
    Validate if the query string follows the 'nid:...' format.

    Args:
        query (str): The query string to validate.

    Returns:
        bool: True if the query is valid (starts with 'nid:' and contains digits),
            False otherwise.
    """
    return bool(query) and query.startswith("nid:") and any(c.isdigit() for c in query)


def check_anki_connect_version() -> Optional[str]:
    """
    Check the version of AnkiConnect and verify if it's reachable.

    Returns:
        Optional[str]: The version string if AnkiConnect is reachable, None otherwise.

    Raises:
        Exception: If there's an error communicating with AnkiConnect.
    """
    url = "http://localhost:8765"
    payload = {"action": "version", "version": 6}
    try:
        response = requests.post(url, json=payload, timeout=5.0)
        response.raise_for_status()
        version = response.json().get("result")
        logger.info(f"AnkiConnect version: {version}")
        return version
    except Exception as exc:
        logger.error(f"Error checking AnkiConnect version: {exc}")
        return None


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    """
    Main entry point for the Anki workflow.

    This function orchestrates the entire workflow:
    1. Reads input data from STDIN
    2. Checks if the operating system is supported
    3. Verifies if Anki is running
    4. Checks AnkiConnect availability
    5. Brings Anki to front and populates the browser with the query

    The function prints a JSON result to stdout containing:
    - anki_status: Current status of Anki
    - success: Boolean indicating if the operation was successful
    - message: Descriptive message about the operation result
    """
    input_data = read_input_data()
    built_nid_list = input_data.get("formatted_nids", "")
    logger.info(f"Received NID list from STDIN: {built_nid_list}")

    result = {"anki_status": "myy_error", "success": False, "message": ""}

    # OS check
    system = platform.system()
    if system not in {"Darwin", "Windows"}:
        result["message"] = f"Unsupported operating system: {system}"
        print(json.dumps(result))
        return

    # Is Anki running?
    if is_program_running("anki"):
        result["anki_status"] = "Anki is running"

        # AnkiConnect reachable?
        version = check_anki_connect_version()
        if version is None:
            result["message"] = "Failed to contact AnkiConnect"
            print(json.dumps(result))
            return

        # Bring window forward & populate browser
        if bring_anki_to_front() and populate_anki_browser(built_nid_list):
            result["success"] = True
            result["message"] = "Successfully opened Anki browser with query"
        else:
            result["message"] = "Failed to focus/populate Anki"
    else:
        result["anki_status"] = "Anki not running"
        result["message"] = "Anki is not running"

    print(json.dumps(result))


if __name__ == "__main__":
    main()