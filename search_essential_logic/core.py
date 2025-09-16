#!/usr/bin/env python3

import os
import json
import re
import numpy as np
import pandas as pd
import h5py
import subprocess
import sys
from loguru import logger
from .data_loader import load_searcher_context
from .myy_api import embedding_service, deepseek_service
from .flow import (
    get_top_n_similarities_and_indices,
    prepare_top_cards_list,
    format_flashcard_results_for_llm,
    chat_with_final_llm
)
from .rerank import rerank_workflow
from typing import List

##################################################
############### Loguru Configuration  ############
##################################################

def configure_logger(level: str = "INFO") -> None:
    """Sets up loguru with console and file output configuration.

    Configures loguru with behavior similar to logging.basicConfig, including
    console output and rotating file output.

    Args:
        level (str): The logging level to use. Defaults to "INFO".

    Returns:
        None

    Raises:
        ValueError: If an invalid logging level is provided.
    """
    fmt = "{time:YYYY-MM-DD HH:mm:ss} - {name} - {level} - {message}"
    logger.remove()                                 # wipe the default sink
    logger.add(sys.stderr, level=level, format=fmt, enqueue=True)
    logger.add(
        "flashcard_search.log",
        rotation="10 MB",
        retention="10 days",
        level=level,
        format=fmt,
        enqueue=True,
    )

# Initialise at import-time so any early log lines are captured.
configure_logger()

# --- Utility Functions ---


##################################################
############### Anki Stuff  #####################
##################################################

def format_nids_for_anki(per_search_result_dictionary: dict) -> dict:
    """Formats extracted NIDs into Anki-compatible string format.
    
    Takes the extracted_nid_list from the search results dictionary, formats them
    into a string with 'nid:' prefix and comma separation, and stores the result
    in the dictionary's formatted_nids key.
    
    Args:
        per_search_result_dictionary (dict): Dictionary containing search results
            with an 'extracted_nid_list' key.
    
    Returns:
        dict: Updated dictionary with formatted NIDs stored in formatted_nids key.
            If input is None or missing required key, returns dictionary with empty
            formatted_nids string.
    """
    if not per_search_result_dictionary or 'extracted_nid_list' not in per_search_result_dictionary:
        per_search_result_dictionary['formatted_nids'] = ""
        return per_search_result_dictionary
    
    nids = per_search_result_dictionary['extracted_nid_list']
    if not nids:
        per_search_result_dictionary['formatted_nids'] = ""
        return per_search_result_dictionary
        
    formatted_nids = f"nid:{','.join(nids)}"
    per_search_result_dictionary['formatted_nids'] = formatted_nids
    return per_search_result_dictionary

def check_anki_status(per_search_result_dictionary: dict = None) -> str:
    """Checks if Anki is running and processes formatted NIDs.

    Verifies Anki's running status and sends formatted NIDs to anki_script.py
    via stdin instead of command-line arguments.

    Args:
        per_search_result_dictionary (dict, optional): Dictionary containing search
            results with formatted_nids. Defaults to None.

    Returns:
        str: Status message indicating Anki's state or error message if something
            went wrong.

    Raises:
        subprocess.SubprocessError: If there's an error running the anki script.
        json.JSONDecodeError: If the response cannot be parsed as JSON.
    """
    # Get the absolute path of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(os.path.dirname(current_dir), "anki_script.py")

    logger.debug(f"Checking Anki status using script: {script}")

    try:
        # Extract the formatted NID string (may be empty)
        formatted_nids = ""
        if per_search_result_dictionary:
            formatted_nids = per_search_result_dictionary.get("formatted_nids", "")
            logger.debug(f"Using formatted NIDs: {formatted_nids}")

        # -------------------------------------------------
        # Send the data to the script via STDIN as JSON
        # -------------------------------------------------
        stdin_payload = json.dumps({"formatted_nids": formatted_nids})

        result = subprocess.run(
            [sys.executable, script],   # Use current Python interpreter (respects venv)
            input=stdin_payload,   # JSON piped through STDIN
            capture_output=True,
            text=True
        )

        # Log any stderr output for debugging
        if result.stderr:
            logger.error(f"Script error output: {result.stderr}")

        # Log the raw stdout for debugging
        logger.debug(f"Raw script output: {result.stdout}")

        # Parse and validate the JSON response
        try:
            response = json.loads(result.stdout)
            if not isinstance(response, dict) or "anki_status" not in response:
                logger.error(f"Invalid response structure: {response}")
                return "Error: Invalid response structure from script"
            return response.get("anki_status", "Error: Invalid response from script")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse script output: {result.stdout}")
            return "Error: Invalid response format from script"

    except Exception as e:
        logger.error(f"Error checking Anki status: {e}")
        return f"Error checking Anki: {e}"


##################################################
############### LLM_rank Stuff  #####################
##################################################


def extract_nid(text: str) -> List[str]:
    """Extracts 13-digit ID numbers from text wrapped in [nid:number] format.

    Searches through the input text for patterns matching [nid:XXXXXXXXXXXXX]
    where X represents digits, and extracts the 13-digit numbers.

    Args:
        text (str): The input text containing NID patterns.

    Returns:
        List[str]: A list of all matched 13-digit numbers in order of appearance.
            Returns empty list if no matches found.

    Example:
        >>> extract_nid("[nid:1234567890123] some text")
        ['1234567890123']
    """
    pattern = r'\[nid:(\d{13})\]'
    nid_list = re.findall(pattern, text)
    return nid_list



def create_llm_ranked_cards(reranked_cards: list, extracted_nids: list) -> list:
    """Creates a list of cards ranked according to LLM output order.
    
    Takes a list of reranked cards and orders them based on the sequence of NIDs
    extracted from the LLM response. Assigns rank numbers starting from 1.
    
    Args:
        reranked_cards (list): List of dictionaries containing card information
            that have been reranked.
        extracted_nids (list): List of NIDs in the order extracted from LLM response.
        
    Returns:
        list: List of card dictionaries with added 'llm_rank' field indicating
            their position in the LLM-determined order.

    Example:
        >>> cards = [{'nid': '123', 'content': 'A'}, {'nid': '456', 'content': 'B'}]
        >>> nids = ['456', '123']
        >>> create_llm_ranked_cards(cards, nids)
        [{'nid': '456', 'content': 'B', 'llm_rank': 1},
         {'nid': '123', 'content': 'A', 'llm_rank': 2}]
    """
    nid_to_card = {card["nid"]: card for card in reranked_cards}
    llm_ranked_cards = []
    
    # Process cards in order of extracted_nid_list
    for rank, nid in enumerate(extracted_nids, 1):
        if nid in nid_to_card:
            ranked_card = nid_to_card[nid].copy()
            ranked_card["llm_rank"] = rank
            llm_ranked_cards.append(ranked_card)
            
    return llm_ranked_cards

##################################################
############### Search Meat  #####################
##################################################

def search_flashcards(runtime_config_dictionary: dict, query_text: str) -> dict:
    """Executes complete flashcard search workflow with reranking.

    Performs a multi-step search process:
    1. Generates query embedding
    2. Finds initial similarity matches
    3. Reranks results using Cohere
    4. Processes through LLM for final ranking
    5. Formats results for Anki integration

    Args:
        runtime_config_dictionary (dict): Configuration dictionary containing:
            - embeddings: Vector embeddings for similarity search
            - top_n_vectors_from_dataframe: Number of initial results to consider
            - dataframe: DataFrame containing flashcard data
            - num_wanted_back_from_cohere: Number of results for reranking
            - personal_LLM_prompt: Template for LLM prompt
            - in_prompt_number: Number to use in prompt formatting
        query_text (str): The search query text.

    Returns:
        dict: Search results dictionary containing:
            - query: Original search query
            - similarity_top_cards_full_fat: Initial similarity matches
            - reranked_cards: Results after Cohere reranking
            - llm_prompt: Prompt sent to LLM
            - llm_response: Response from LLM
            - extracted_nid_list: List of extracted NIDs
            - formatted_nids: NIDs formatted for Anki
            - anki_status: Status of Anki connection
            - llm_ranked_cards: Final ranked card list
        Returns None if an error occurs during processing.

    Raises:
        Exception: If any step in the search workflow fails.
    """
    logger.info(f"Running search for query: {query_text}")

    try:
        # Get query embedding
        query_embed = embedding_service.get_embedding(query_text)

        # Get initial similarity matches
        top_indices_sim, top_similarities = get_top_n_similarities_and_indices(
            query_embed,
            runtime_config_dictionary["embeddings"],
            runtime_config_dictionary["top_n_vectors_from_dataframe"]
        )

        # Prepare initial card listing
        similarity_top_cards_full_fat = prepare_top_cards_list(
            top_indices_sim, 
            top_similarities, 
            runtime_config_dictionary["dataframe"]
        )

        # Rerank using Cohere
        reranked_cards = rerank_workflow(
            query_text,
            similarity_top_cards_full_fat,
            runtime_config_dictionary["num_wanted_back_from_cohere"]
        )

        # Format for LLM
        header_that_is_prompt = runtime_config_dictionary["personal_LLM_prompt"].format(
            in_prompt_number=runtime_config_dictionary["in_prompt_number"]
        )
        llm_prompt = format_flashcard_results_for_llm(
            header_that_is_prompt, query_text, reranked_cards
        )

        # ChatGPT
        back_from_chatgpt = chat_with_final_llm(llm_prompt)

        # Extract NIDs from ChatGPT response
        extracted_nids = extract_nid(back_from_chatgpt)

        # -------------------------------------------------
        # Replace old code-block extraction with NID format
        # -------------------------------------------------
        # Build initial result dict (extracted_code will be filled next)
        per_search_result_dictionary = {
            "query": query_text,
            "similarity_top_cards_full_fat": similarity_top_cards_full_fat,
            "reranked_cards": reranked_cards,
            "llm_prompt": llm_prompt,
            "llm_response": back_from_chatgpt,
            "extracted_nid_list": extracted_nids,
            "formatted_nids": "",        # placeholder – will be filled below
            "anki_status": None,         # placeholder – will be filled below
            "llm_ranked_cards": []       # placeholder – will be filled below
        }

        # --- Populate the placeholders in the correct order ---

        # 1️⃣  Assign values to "formatted_nids" key to fill placeholder
        per_search_result_dictionary = format_nids_for_anki(per_search_result_dictionary)
        formatted_nids = per_search_result_dictionary["formatted_nids"]

        # 2️⃣  Assign values to "llm_ranked_cards" key to fill placeholder
        per_search_result_dictionary["llm_ranked_cards"] = create_llm_ranked_cards(
            reranked_cards, extracted_nids
        )

        # 3️⃣  Assign value to "anki_status" key to fill placeholder
        per_search_result_dictionary["anki_status"] = check_anki_status(
            per_search_result_dictionary
        )

        logger.info("Search workflow completed successfully")
        return per_search_result_dictionary
    except Exception as e:
        logger.exception(f"Error in search_flashcards: {e}")
        return None

