"""
Search Essential Logic - A package for semantic search over flashcards.

This package provides functionality for loading and searching through flashcard data
using semantic embeddings and natural language processing.
"""

from .data_loader import load_from_hdf5, load_searcher_context
from .core import search_flashcards, configure_logger
from .myy_api import embedding_service, deepseek_service
from .flow import (
    get_top_n_similarities_and_indices,
    prepare_top_cards_list,
    format_flashcard_results_for_llm
)

__all__ = [
    'load_from_hdf5',
    'load_searcher_context',
    'search_flashcards',
    'configure_logger',
    'embedding_service',
    'deepseek_service',
    'get_top_n_similarities_and_indices',
    'prepare_top_cards_list',
    'format_flashcard_results_for_llm',
] 