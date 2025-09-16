#!/usr/bin/env python3
"""Command line interface for running flashcard searches.

This is only a test for verifying that the essential logic of the program is working,
and so is not for regular use.

This module provides a CLI tool for searching flashcards using various output formats
and logging levels. It supports JSON output, rich colored output, and configurable
logging verbosity.

Example:
    Basic usage:
        $ python3 manual_test_search.py --query "pneumonia findings"
    
    With JSON output:
        $ python3 manual_test_search.py --query "pneumonia findings" --json
"""

import sys
import json
import argparse
from rich.console import Console
from rich.json import JSON
from search_essential_logic import search_flashcards, configure_logger, load_searcher_context

def main():
    """Parse command line arguments and execute flashcard search.
    
    The function sets up argument parsing, handles the display of a help guide when
    no query is provided, and executes the search with the specified configuration.
    
    Returns:
        None
    
    Raises:
        SystemExit: If an error occurs during execution or if no query is provided.
    """
    parser = argparse.ArgumentParser(
        description="Run one flashcard search end-to-end"
    )
    parser.add_argument(
        "--config",
        default="search_essential_logic/config.json",
        help="path to your config JSON"
    )
    parser.add_argument(
        "--query",
        help="the text you want to search"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="output results as JSON"
    )
    parser.add_argument(
        "--rich",
        action="store_true",
        help="display results as rich colored JSON"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level"
    )
    args = parser.parse_args()
    
    # Set log level from command line if provided
    if args.log_level:
        configure_logger(args.log_level)

    # ------------------------------------------------------------------
    # Friendly CLI Quick-Guide for non-programmers
    # ------------------------------------------------------------------
    script_name = "cli_test_for_essential_logic.py"
    guide_text = f"""
===============================================================================
FLASHCARD SEARCH — COMMAND-LINE QUICK GUIDE
===============================================================================

1) Basic search
   $ python3 {script_name} --query "pneumonia findings"

2) Choose an output format
   • Pure JSON (for programs)        
     $ python3 {script_name} --query "pneumonia findings" --json
   • Rich (colourised)              
     $ python3 {script_name} --query "pneumonia findings" --rich

3) Verbosity / Logging
   Add --log-level <LEVEL> to any command. Levels: DEBUG > INFO > WARNING > ERROR > CRITICAL
   Example (max detail):
     $ python3 {script_name} --query "pneumonia findings" --json --log-level DEBUG

-------------------------------------------------------------------------------
Flag reference
   --config     Path to config file (default: {args.config})
   --query      Text to search for
   --json       Raw JSON output
   --rich       Colourised output
   --log-level  Logging verbosity

Copy & paste any command above directly into your terminal.
===============================================================================
"""

    # Show guide and exit when no query is supplied
    if not args.query:
        print(guide_text)
        sys.exit(0)

    try:
        runtime_config_dictionary = load_searcher_context(args.config)
        result = search_flashcards(runtime_config_dictionary, args.query)

        if args.json:
            # Output as JSON for machine consumption
            print(json.dumps(result, indent=2))
        elif args.rich:
            # Output as rich colored JSON
            console = Console()
            json_str = json.dumps(result, indent=2)
            console.print(JSON(json_str))
        else:
            # No output flag supplied – gently remind the user and re-show the guide
            print("\n⚠️  No output format selected.")
            print("   Please add --json, --pprint or --rich.\n")
            print(guide_text)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 