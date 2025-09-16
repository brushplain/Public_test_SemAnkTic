import numpy as np
from loguru import logger
from .myy_api import deepseek_service

def get_top_n_similarities_and_indices(query_embed, embeddings, top_n_sim):
    """Computes similarities and returns top indices in one operation.
    
    Args:
        query_embed: The query embedding vector to compare against
        embeddings: Matrix of embeddings to compare with query
        top_n_sim: Number of top matches to return
        
    Returns:
        tuple: (top_indices_sim, top_similarities) containing arrays of the 
               top N indices and their corresponding similarity scores
               
    Raises:
        ValueError: If embedding dimensions don't match
    """
    logger.debug(f"Computing top {top_n_sim} matches")
    
    query_vector = np.asarray(query_embed, dtype=np.float32).reshape(-1)
    embeddings_matrix = np.asarray(embeddings, dtype=np.float32)
    
    # Check dimensions match
    if query_vector.shape[0] != embeddings_matrix.shape[1]:
        raise ValueError(
            f"Embedding dimension mismatch: query vector has {query_vector.shape[0]} dimensions "
            f"but embeddings matrix expects {embeddings_matrix.shape[1]} dimensions"
        )
    
    # Normalize query
    q_norm = np.linalg.norm(query_vector)
    query_normed = query_vector / q_norm if q_norm != 0 else query_vector
    
    # Normalize embeddings row-wise
    emb_norms = np.linalg.norm(embeddings_matrix, axis=1, keepdims=True)
    emb_norms[emb_norms == 0] = 1.0
    emb_normed = embeddings_matrix / emb_norms
    
    # Compute similarities and get top matches in one pass
    similarity_scores = emb_normed @ query_normed
    logger.info("Completed cosine similarity calculations for all embeddings")
    
    top_indices_sim = np.argpartition(similarity_scores, -top_n_sim)[-top_n_sim:]
    top_indices_sim = top_indices_sim[np.argsort(similarity_scores[top_indices_sim])[::-1]]
    top_similarities = similarity_scores[top_indices_sim]
    
    return top_indices_sim, top_similarities


def prepare_top_cards_list(top_indices_sim, top_similarities, dataframe):
    """Prepares a list of top cards from search results.
    
    Args:
        top_indices_sim: Array of indices for top matches
        top_similarities: Array of similarity scores
        dataframe: DataFrame containing flashcard data
        
    Returns:
        list: List of dictionaries containing ranked card information
    """
    similarity_top_cards_full_fat = []
    for cosine_similarity_rank, (top_index_sim, similarity) in enumerate(zip(top_indices_sim, top_similarities), 1):
        row = dataframe.iloc[top_index_sim]
        similarity_top_cards_full_fat.append({
            "cosine_similarity_rank": cosine_similarity_rank,
            "nid": str(row["nid"]),
            "cosine_similarity_score": float(similarity),
            "content": row["flashcard_content"],
        })
    return similarity_top_cards_full_fat


def format_flashcard_results_for_llm(header_that_is_prompt, query_text, reranked_cards):
    """Builds a formatted prompt string for LLM processing of flashcard results.

    Args:
        header_that_is_prompt: Text to appear at the top of results.
        query_text: Original search query.
        reranked_cards: List of dictionaries containing ranked card information,
                       already sorted by relevance_rank.

    Returns:
        str: Formatted string containing flashcard results for LLM processing.
    """
    output_to_llm = f"# Prompt\n{header_that_is_prompt}\n\n"
    output_to_llm += f"## Query\n{query_text}\n\n"
    output_to_llm += "## Flashcard Pool\n"
    for full_dictionary_single_card in reranked_cards:
        nid = full_dictionary_single_card["nid"]
        content = full_dictionary_single_card["content"]
        output_to_llm += f"- [nid:{nid}] {content}\n"
    return output_to_llm

def chat_with_final_llm(llm_prompt):
    """Sends text to DeepSeek's chat API and returns the response.

    Args:
        llm_prompt: Text prompt to send to the API.

    Returns:
        str: Response from the DeepSeek API or error message if request fails.
    """
    logger.info("Sending request to DeepSeek API")
    try:
        return deepseek_service.chat_completion(llm_prompt)
    except Exception as e:
        logger.exception(f"Error calling DeepSeek API: {e}")
        return f"Error: {e}"