from openai import OpenAI
from loguru import logger
import os
from dotenv import load_dotenv
import numpy as np
from typing import List, Dict, Any
import requests
import time
from huggingface_hub import InferenceClient
import json

class QwenEmbeddingService:
    """Service for generating text embeddings using Qwen3-Embedding-8B model via Nebius AI.
    
    This service uses the OpenAI-compatible API provided by Nebius.
    Requires NEBIUS_API_KEY environment variable to be set.
    """
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("NEBIUS_API_KEY")
        if not self.api_key:
            logger.error("NEBIUS_API_KEY not found in environment variables")
            raise ValueError("NEBIUS_API_KEY not found in environment variables")
        
        self.client = OpenAI(
            base_url="https://api.studio.nebius.com/v1/",
            api_key=self.api_key
        )
        self.model = "Qwen/Qwen3-Embedding-8B"
        
        # Load instruction settings from config
        try:
            with open("search_essential_logic/config.json", "r") as f:
                config = json.load(f)
                self.use_instruction = config["embedding_settings"]["use_instruction"]
                self.instruction = config["embedding_settings"]["instruction"]
        except Exception as e:
            logger.warning(f"Failed to load instruction settings from config: {e}")
            self.use_instruction = False
            self.instruction = None
    
    def get_embedding(self, text: str) -> np.ndarray:
        """Get embedding vector for input text."""
        try:
            logger.info("embed api call")
            start = time.perf_counter()

            # Add instruction if enabled
            if self.use_instruction and self.instruction:
                text = f"{self.instruction}\n\n{text}"

            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )

            duration = time.perf_counter() - start
            logger.info(f"embed api answer (took {duration:.2f}s)")
            
            # Extract embedding from response and convert to numpy array
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
                
            return embedding
        except Exception as e:
            logger.exception(f"Error getting embedding: {e}")
            raise

class DeepSeekService:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
    
    def chat_completion(self, prompt: str, model: str = "deepseek-chat") -> str:
        """Get chat completion response."""
        try:
            logger.info("llm api call")
            start = time.perf_counter()

            resp = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            duration = time.perf_counter() - start
            logger.info(f"llm api answer (took {duration:.2f}s)")

            return resp.choices[0].message.content
        except Exception as e:
            logger.exception(f"Error calling DeepSeek API: {e}")
            raise

class CohereService:
    """Service for reranking documents using Cohere's API.
    
    Requires COHERE_API_KEY environment variable to be set.
    """
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("COHERE_API_KEY")
        if not self.api_key:
            logger.error("COHERE_API_KEY not found in environment variables")
            raise ValueError("COHERE_API_KEY not found in environment variables")
        
        self.base_url = "https://api.cohere.ai/v2/rerank"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Client-Name": "flashcard-search"
        }

    def rerank(self, query: str, documents: List[str], top_n: int = None) -> Dict[str, Any]:
        """Call Cohere's rerank API.
        
        Args:
            query: Search query string
            documents: List of document strings to rerank
            top_n: Optional number of top results to return
            
        Returns:
            Dict containing reranking results
            
        Raises:
            requests.exceptions.RequestException: If API call fails
        """
        try:
            payload = {
                "model": "rerank-v3.5",
                "query": query,
                "documents": documents,
            }
            if top_n is not None:
                payload["top_n"] = top_n

            start = time.perf_counter()
            logger.info(f"Calling Cohere rerank API with {len(documents)} documents")
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            duration = time.perf_counter() - start
            logger.info(f"reranker api answer (took {duration:.2f}s)")

            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.exception(f"Cohere API call failed: {e}")
            raise

# Replace the JinaEmbeddingService instance with QwenEmbeddingService
embedding_service = QwenEmbeddingService()
deepseek_service = DeepSeekService()
cohere_service = CohereService()
