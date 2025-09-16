from typing import List, Dict, Any, Tuple
from loguru import logger
from .myy_api import cohere_service

def prepare_for_cohere(similarity_top_cards_full_fat: List[Dict]) -> Tuple[List[str], Dict[int, Dict]]:
    """Prepare data for Cohere reranking.
    
    Args:
        similarity_top_cards_full_fat: List of card dictionaries from initial similarity search
        
    Returns:
        Tuple containing:
        - List of content strings for Cohere
        - Dictionary mapping indices to original card data
    """
    logger.debug("Preparing data for Cohere reranking")
    content_list_for_cohere = []
    cohere_pre_rank_index = {}

    for i, full_dictionary_single_card in enumerate(similarity_top_cards_full_fat):
        content_list_for_cohere.append(full_dictionary_single_card["content"])
        cohere_pre_rank_index[i] = full_dictionary_single_card

    return content_list_for_cohere, cohere_pre_rank_index

def reconstruct_from_cohere(
    cohere_response: Dict[str, Any], 
    cohere_pre_rank_index: Dict[int, Dict]
) -> List[Dict]:
    """Reconstruct card data using Cohere response.
    
    Args:
        cohere_response: Response from Cohere API
        cohere_pre_rank_index: Mapping of indices to original card data
        
    Returns:
        List of reranked cards with added relevance scores, sorted by relevance_rank
    """
    logger.debug("Reconstructing card data from Cohere response")
    reranked_cards = []
    
    # Process results in order (Cohere returns them sorted by relevance)
    for relevance_rank, cohere_result in enumerate(cohere_response["results"], start=1):
        try:
            original_card = cohere_pre_rank_index[cohere_result["index"]]
            card = original_card.copy()
            card["relevance_score"] = cohere_result["relevance_score"]
            card["relevance_rank"] = relevance_rank
            reranked_cards.append(card)
        except KeyError as e:
            logger.error(f"Failed to find original card for index {cohere_result['index']}: {e}")
            continue

    # Double-check the order is maintained by relevance_rank
    reranked_cards.sort(key=lambda x: x["relevance_rank"])
    
    return reranked_cards

def rerank_workflow(
    query: str,
    similarity_top_cards_full_fat: List[Dict],
    num_wanted_back_from_cohere: int = None
) -> List[Dict]:
    """Execute complete reranking workflow.
    
    Args:
        query: Original search query
        similarity_top_cards_full_fat: List of cards from initial similarity search
        num_wanted_back_from_cohere: Number of results to request from Cohere. 
                                    If None, will return all results.
        
    Returns:
        List of reranked cards
        
    Raises:
        Exception: If reranking fails
    """
    try:
        logger.info(f"Starting reranking workflow for query: {query}")
        
        if not similarity_top_cards_full_fat:
            logger.warning("No cards provided for reranking")
            return []
            
        # Prepare data for Cohere
        content_list, pre_rank_index = prepare_for_cohere(similarity_top_cards_full_fat)
        
        # Call Cohere API
        cohere_response = cohere_service.rerank(
            query=query,
            documents=content_list,
            top_n=num_wanted_back_from_cohere if num_wanted_back_from_cohere else None
        )
        
        # Reconstruct results
        reranked_cards = reconstruct_from_cohere(cohere_response, pre_rank_index)
        
        logger.info(f"Reranking workflow completed successfully with {len(reranked_cards)} results")
        return reranked_cards
        
    except Exception as e:
        logger.exception("Reranking workflow failed")
        raise 