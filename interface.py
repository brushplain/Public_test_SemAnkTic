#!/usr/bin/env python3
# =============================================================================
# Non-Core Module
# -----------------------------------------------------------------------------
# This is the user-facing layer of the program. It prompts the user for input,
# displays results in a readable format.
#
# All core functionality—like similarity search, LLM interaction, code extraction,
# clipboard copying, and launching Anki—is handled by the core.py file.
#
# This script exists to keep user interaction and display logic separate,
# allowing core.py to stay focused on the essential logic of the program.
# =============================================================================

from search_essential_logic import load_searcher_context, search_flashcards, configure_logger
import textwrap
import json
import argparse
import subprocess
import shutil
from rich.console import Console
from rich.progress import Progress
from rich.panel import Panel
from rich.table import Table
from rich.box import ROUNDED
from rich import print as rprint
from rich.markdown import Markdown
import os
import re
from loguru import logger

# Configure logging to only show errors
configure_logger("ERROR")

# Add asciichartpy for terminal plotting
try:
    import asciichartpy as acp
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("Note: Install 'asciichartpy' for similarity score visualization: pip install asciichartpy")

console = Console()

def display_stats(flashcard_count: int, embedding_count: int) -> None:
    """Displays the count of loaded flashcards and embeddings.

    Args:
        flashcard_count (int): Number of flashcards loaded.
        embedding_count (int): Number of embeddings loaded.

    Returns:
        None
    """
    console.print(f"[green]✓[/] Loaded {flashcard_count} flashcards and {embedding_count} embeddings")

def create_similarity_plot(top_cards_sim: list, width: int = 140) -> str:
    """Creates a terminal-friendly line plot of similarity scores.

    Creates a plot that always fits the specified width by:
    1. Computing how many columns the y-axis labels consume
    2. Down-sampling the data to the remaining horizontal space

    Args:
        top_cards_sim (list): List of dictionaries containing flashcard data with similarity scores.
        width (int, optional): Maximum width of the plot in characters. Defaults to 140.

    Returns:
        str: ASCII art plot of similarity scores, or None if plotting is not available
            or there are insufficient data points.
    """
    if not PLOTTING_AVAILABLE or len(top_cards_sim) < 2:
        return None

    scores = [card["cosine_similarity_score"] for card in top_cards_sim]

    # ---------------------------------------------------------------
    # 1) How wide are the labels on the left side of the chart?
    # ---------------------------------------------------------------
    fmt = "{:7.3f}"                        # keep labels compact
    label_max = fmt.format(max(scores))
    label_min = fmt.format(min(scores))
    offset = max(len(label_max), len(label_min)) + 2   # +2 for " ┤"

    # ---------------------------------------------------------------
    # 2) Down-sample so (offset + series_len) ≤ width
    # ---------------------------------------------------------------
    available_cols = max(1, width - offset)
    target_len = min(available_cols, len(scores))

    if len(scores) > target_len:
        ratio = len(scores) / target_len
        compressed = []
        for i in range(target_len):
            start = int(i * ratio)
            end   = int((i + 1) * ratio)
            seg   = scores[start:end] or [scores[start]]
            compressed.append(sum(seg) / len(seg))
        plot_scores = compressed
    else:
        plot_scores = scores

    plot_cfg = {
        "height": 12,
        "format": fmt,
    }

    try:
        return acp.plot(plot_scores, cfg=plot_cfg)
    except Exception:
        return None

def format_flashcard_results_for_terminal(
    per_search_result_dictionary: dict,
    max_length: int = 100
) -> None:
    """Formats and displays flashcard search results in the terminal.

    Args:
        per_search_result_dictionary (dict): Complete search result dictionary containing:
            - query: Original search query
            - similarity_top_cards_full_fat: List of ranked flashcard results
            - llm_response: Language model response (optional)
            - anki_status: Anki application status
        max_length (int, optional): Maximum length for truncating content. Defaults to 100.
    """
    # Set a consistent width for both elements
    table_width = 160
    
    # Note: We read the config file directly here instead of using runtime_config_dictionary
    # because display settings are purely interface-related and not part of the core program logic.
    # The runtime_config_dictionary is reserved for core functionality like search and ranking,
    # while interface.py handles only display-related features.
    config_path = "search_essential_logic/config.json"
    with open(config_path) as f:
        config = json.load(f)
    display_settings = config.get('display_settings', {})
    show_context_window = display_settings.get('show_context_window', True)  # Default to True if not specified
    show_similarity_pattern = display_settings.get('show_similarity_pattern', True)  # Default to True if not specified
    
    # Only show Context Window if enabled
    if show_context_window:
        # Add Context window header
        console.print("\n[bold cyan]Context Window:[/bold cyan]")
        
        # Create a rich table with the same width
        table = Table(box=ROUNDED, width=table_width)
        table.add_column("Cohere", style="cyan", justify="center")
        table.add_column("NID", style="magenta")
        table.add_column("Content", style="#E0E0E0")
        
        for card in per_search_result_dictionary['reranked_cards']:
            table.add_row(
                str(card['relevance_rank']),
                f"{card['nid']}",
                textwrap.shorten(str(card['content']), width=max_length, placeholder="…")
            )
        
        console.print(table)
    
    # Only show Similarity Score Pattern if enabled
    if show_similarity_pattern and len(per_search_result_dictionary['similarity_top_cards_full_fat']) > 1:
        similarity_plot = create_similarity_plot(
            per_search_result_dictionary['similarity_top_cards_full_fat'], 
            width=table_width-10
        )
        if similarity_plot:
            console.print("\n")
            console.print(Panel(
                similarity_plot, 
                title="[bold cyan]Similarity Score Pattern[/bold cyan]", 
                box=ROUNDED, 
                width=table_width,
                subtitle="[dim]Shape shows score distribution across results[/dim]"
            ))
    
    # After similarity plot and before formatted NIDs, add new LLM ranking table
    if per_search_result_dictionary.get('llm_ranked_cards'):
        console.print("\n\n[bold cyan]LLM Ranked Results:[/bold cyan]")
        llm_table = Table(box=ROUNDED, width=table_width)
        llm_table.add_column("LLM Rank", style="yellow", justify="center")
        llm_table.add_column("Relevance Rank", style="cyan", justify="center")
        llm_table.add_column("Embedding Rank", style="green", justify="center")
        llm_table.add_column("NID", style="magenta", justify="center")
        llm_table.add_column("Relevance Score", style="cyan", justify="center")
        llm_table.add_column("Similarity Score", style="green", justify="center")
        
        for card in per_search_result_dictionary['llm_ranked_cards']:
            llm_table.add_row(
                str(card['llm_rank']),
                str(card['relevance_rank']),
                str(card['cosine_similarity_rank']),
                str(card['nid']),
                f"{card['relevance_score']:.4f}",
                f"{card['cosine_similarity_score']:.4f}"
            )
        
        console.print(llm_table)
    
    # Display formatted NIDs if available (without box)
    if per_search_result_dictionary.get('formatted_nids'):
        console.print("\n\n[bold cyan]Formatted NIDs:[/bold cyan]")
        console.print(per_search_result_dictionary['formatted_nids'], style="#E0E0E0")
    
    # Display LLM response if provided, rendered as markdown
    if per_search_result_dictionary.get('llm_response'):
        console.print("\n\n[bold cyan]LLM Response:[/bold cyan]")
        markdown_content = Markdown(per_search_result_dictionary['llm_response'], style="#E0E0E0")
        console.print(markdown_content)

def display_welcome_art() -> None:
    """Displays ASCII art welcome message from file.

    Reads and displays the contents of 'ascii_art.txt' with appropriate styling.

    Args:
        None

    Returns:
        None

    Raises:
        FileNotFoundError: If ascii_art.txt file is not found.
    """
    with open('ascii_art.txt', 'r') as f:
        art = f.read()
    console.print("\n" + art + "\n", style="#E0E0E0")

# ─────────────────────────────────────────────────────────────
# Friendly progress handler – builds a cumulative timeline
# ─────────────────────────────────────────────────────────────
class SearchProgressHandler:
    PREFIX = "Searching flashcards…"

    def __init__(self, console: Console):
        self.console = console
        self.status_cm = None
        self.parts: list[str] = []

    def _render(self) -> None:
        suffix = " → ".join(self.parts)
        self.status_cm.update(f"[cyan]{self.PREFIX} {suffix}")

    def _add(self, part: str) -> None:
        root = part.split(" (")[0]
        if not any(p.startswith(root) for p in self.parts):
            self.parts.append(part)
            self._render()

    def __enter__(self):
        self.status_cm = self.console.status(f"[cyan]{self.PREFIX}", spinner="dots")
        self.status_cm.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.status_cm:
            final_text = self.status_cm.renderable  # Save the last status line
            self.status_cm.stop()                   # Stop spinner and clear line
            self.console.print(final_text)          # Print the final status as a normal line

    def __call__(self, msg):
        text: str = msg.record["message"]

        # embed
        if "embed api call" in text:
            self._add("embed api call")
        elif text.startswith("embed api answer"):
            m = re.search(r"\(took ([0-9.]+)s\)", text)
            dur = f" ({m.group(1)}s)" if m else ""
            self._add(f"embed api answer{dur}")

        # similarity
        elif "Completed cosine similarity" in text:
            self._add("compute similarity")

        # reranker
        elif "Calling Cohere rerank API" in text:
            self._add("reranker api call")
        elif text.startswith("reranker api answer"):
            m = re.search(r"\(took ([0-9.]+)s\)", text)
            dur = f" ({m.group(1)}s)" if m else ""
            self._add(f"reranker api answer{dur}")

        # llm
        elif "llm api call" in text:
            self._add("llm api call")
        elif text.startswith("llm api answer"):
            m = re.search(r"\(took ([0-9.]+)s\)", text)
            dur = f" ({m.group(1)}s)" if m else ""
            self._add(f"llm api answer{dur}")

        # finished
        elif "Search workflow completed" in text:
            self._add("Success!")

def main() -> None:
    """Main entry point for the flashcard search application.

    Handles the flashcard search workflow:
    - Loads configuration and data
    - Processes user queries
    - Displays search results
    - Handles interactive search mode

    Returns:
        None
    """
    # Use direct config path instead of command line arg
    config_path = "search_essential_logic/config.json"

    # Get the HDF5 file path from the config first
    with open(config_path) as f:
        config = json.load(f)
    full_path = config.get('myy_hdf5_location', {}).get('h5_file', 'path not found')
    
    # Get just the filename if path is found
    if full_path != 'path not found':
        h5_path = os.path.basename(full_path)
    else:
        h5_path = full_path

    with Progress(transient=True) as progress:
        task = progress.add_task("Loading Data...", total=None)  # Indeterminate spinner
        runtime_config_dictionary = load_searcher_context(config_path)
        progress.stop()
    
    # Display single-line completion message
    flashcard_count = len(runtime_config_dictionary.get('dataframe', []))
    console.print(f"Loaded {flashcard_count:,} Notes from {h5_path}")
    
    # Add clear visual separation with multiple newlines
    console.print("\n\n\n")

    query = None
    while True:
        if not query:
            console.print("[dim]Enter your search query ('quit' to exit)[/]")
            query = console.input("[cyan]>>> [/]")
            # Add three newlines after input for consistent spacing with results
            console.print("\n\n\n")
            
        if not query or query.lower() == 'quit':
            break

        try:
            # attach progress handler as a temporary Loguru sink
            progress = SearchProgressHandler(console)
            sink_id = logger.add(progress, level="INFO")

            with progress:                                   # shows spinner
                per_search_result_dictionary = search_flashcards(
                    runtime_config_dictionary, query
                )

            logger.remove(sink_id)                           # clean up sink

            format_flashcard_results_for_terminal(per_search_result_dictionary)

            # Add two blank lines before next prompt
            console.print("\n\n")

        except Exception as e:
            console.print(f"[red]Error:[/] {e}")
        
        query = None

if __name__ == "__main__":
    display_welcome_art()
    main()