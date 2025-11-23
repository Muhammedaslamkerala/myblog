import requests
import json
import numpy as np
from django.conf import settings
from django.utils.html import strip_tags
from sentence_transformers import SentenceTransformer
import re
from functools import lru_cache
from typing import Union, List, Tuple, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ratelimit import limits, sleep_and_retry
import time
import logging

logger = logging.getLogger(__name__)

class AIService:
    """AI service with RAG capabilities, retries, and rate limiting"""
    
    # Rate limit: Adjust based on Groq plan (e.g., 30 RPM -> 20/min safe)
    CALLS_PER_MINUTE = 20
    RATE_LIMIT_WINDOW = 60  # seconds
    
    def __init__(self):
        self.api_key = getattr(settings, 'GROQ_API_KEY', None)
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"
        
        # Load embedding model (free, local)
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load embedding model: {e}")
            self.embedding_model = None
        
        # In-memory cache for summaries/embeddings (expires after 1h)
        self._cache = {}
    
    @sleep_and_retry
    @limits(calls=CALLS_PER_MINUTE, period=RATE_LIMIT_WINDOW)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(requests.exceptions.HTTPError)
    )
    def _call_api(self, messages, max_tokens=1000, temperature=0.7):
        """Call Groq API with retries and rate limiting"""
        if not self.api_key:
            logger.error("GROQ_API_KEY not set")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content'].strip()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Rate limit hit: {e}. Retrying...")
                raise
            logger.error(f"API HTTP Error: {e}")
            return None
        except Exception as e:
            logger.error(f"AI API Error: {e}")
            return None
    
    def _get_cache_key(self, func_name, *args, **kwargs):
        """Generate cache key for non-lru methods"""
        arg_str = str(args) + str(kwargs)
        return f"{func_name}_{hash(arg_str)}"
    
    def chunk_text(self, text, chunk_size=500, overlap=100):
        """Split text into overlapping chunks"""
        text = strip_tags(text).strip()
        if not text:
            return []
        
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        return chunks
    
    @lru_cache(maxsize=128)
    def create_embeddings(self, texts_input: Union[List[str], Tuple[str, ...]]):
        """Create embeddings for text chunks (cached; accepts list or tuple)"""
        # FIX: Ensure input is a tuple for hashing
        if isinstance(texts_input, list):
            texts_input = tuple(texts_input)
        elif not isinstance(texts_input, tuple):
            raise ValueError("Input must be list or tuple of strings")
        
        texts = list(texts_input)
        if not texts or not self.embedding_model:
            return None
        
        try:
            embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
            return embeddings
        except Exception as e:
            logger.error(f"Embedding Error: {e}")
            return None
    
    def find_relevant_chunks(self, query, chunks, embeddings, top_k=3):
        """Find most relevant chunks using cosine similarity"""
        if not self.embedding_model or embeddings is None or not chunks:
            return chunks[:top_k] if chunks else []
        
        try:
            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)[0]
            similarities = np.dot(embeddings, query_embedding) / (
                np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
            )
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            return [chunks[i] for i in top_indices if i < len(chunks)]
        except Exception as e:
            logger.error(f"Retrieval Error: {e}")
            return chunks[:top_k] if chunks else []
    
    def generate_tags(self, title, content, max_tags=5):
        """Auto-generate tags (cached)"""
        content = strip_tags(content).strip()
        if not content:
            return []
        
        cache_key = self._get_cache_key("generate_tags", title[:50], content[:100])
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        clean_content = content[:1500]
        prompt = f"Generate {max_tags} relevant tags for this blog post.\nTitle: {title}\nContent: {clean_content}\nReturn ONLY comma-separated tags (lowercase, 2-3 words each). Tags:"
        messages = [
            {"role": "system", "content": "You generate relevant tags for blog posts."},
            {"role": "user", "content": prompt}
        ]
        result = self._call_api(messages, max_tokens=100, temperature=0.5)
        if result:
            tags = [tag.strip().lower() for tag in result.split(',')]
            tags = [tag for tag in tags if 0 < len(tag) < 50][:max_tags]
            self._cache[cache_key] = tags
            return tags
        return []
    
    def suggest_category(self, title, content, available_categories):
        """Suggest best category (cached)"""
        content = strip_tags(content).strip()
        if not content:
            return None
        
        cache_key = self._get_cache_key("suggest_category", title[:50], content[:100])
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        clean_content = content[:1500]
        category_list = ", ".join([cat.name for cat in available_categories])
        prompt = f"Which ONE category fits best?\nTitle: {title}\nContent: {clean_content}\nCategories: {category_list}\nReturn ONLY the category name:"
        messages = [
            {"role": "system", "content": "You categorize blog posts accurately."},
            {"role": "user", "content": prompt}
        ]
        result = self._call_api(messages, max_tokens=50, temperature=0.3)
        if result:
            result_lower = result.lower().strip()
            for category in available_categories:
                if category.name.lower() in result_lower:
                    self._cache[cache_key] = category
                    return category
        return None
    
    def generate_summary(self, content, num_lines=3):
        """Generate summary (cached)"""
        content = strip_tags(content).strip()
        if not content:
            return "No content available for summary."
        
        clean_content = content[:2000]
        cache_key = self._get_cache_key("generate_summary", clean_content[:100])
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        prompt = f"Summarize in {num_lines} concise lines:\n{clean_content}\nSummary:"
        messages = [
            {"role": "system", "content": "You create clear, concise summaries."},
            {"role": "user", "content": prompt}
        ]
        result = self._call_api(messages, max_tokens=200, temperature=0.6)
        summary = result or "Unable to generate summary."
        self._cache[cache_key] = summary
        return summary
    
    def answer_with_rag(self, question, title, chunks, embeddings):
        """Answer question using RAG"""
        if not chunks:
            return "No content available to answer this question."
        
        relevant_chunks = self.find_relevant_chunks(question, chunks, embeddings, top_k=3)
        if not relevant_chunks:
            return "Unable to find relevant information to answer this question."
        
        context = "\n\n".join(relevant_chunks[:2])
        prompt = f"Answer based ONLY on this context from '{title}':\n{context}\n\nQuestion: {question}\nAnswer:"
        messages = [
            {"role": "system", "content": "You answer questions accurately using only provided context."},
            {"role": "user", "content": prompt}
        ]
        return self._call_api(messages, max_tokens=500, temperature=0.7) or "Unable to answer based on available context."
    
    def explain_point_by_point(self, content):
        """Explain content point by point (cached)"""
        content = strip_tags(content).strip()
        if not content:
            return "No content available for explanation."
        
        clean_content = content[:2000]
        cache_key = self._get_cache_key("explain_point_by_point", clean_content[:100])
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        prompt = f"Explain point by point (numbered list):\n{clean_content}\nExplanation:"
        messages = [
            {"role": "system", "content": "You explain clearly with numbered points."},
            {"role": "user", "content": prompt}
        ]
        result = self._call_api(messages, max_tokens=800, temperature=0.6) or "Unable to explain."
        self._cache[cache_key] = result
        return result
    
    def generate_study_questions(self, content, num_questions=5):
        """Generate study questions (cached)"""
        content = strip_tags(content).strip()
        if not content:
            return "No content available for generating questions."
        
        clean_content = content[:2000]
        cache_key = self._get_cache_key("generate_study_questions", clean_content[:100], num_questions)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        prompt = f"Create {num_questions} questions (mix MCQ/short answer):\n{clean_content}\nQuestions:"
        messages = [
            {"role": "system", "content": "You create educational questions."},
            {"role": "user", "content": prompt}
        ]
        result = self._call_api(messages, max_tokens=600, temperature=0.7) or "Unable to generate questions."
        self._cache[cache_key] = result
        return result
    
    def get_key_takeaways(self, content, num_points=5):
        """Extract key takeaways (cached)"""
        content = strip_tags(content).strip()
        if not content:
            return "No content available for takeaways."
        
        clean_content = content[:2000]
        cache_key = self._get_cache_key("get_key_takeaways", clean_content[:100], num_points)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        prompt = f"List {num_points} key takeaways:\n{clean_content}\nTakeaways:"
        messages = [
            {"role": "system", "content": "You extract key insights."},
            {"role": "user", "content": prompt}
        ]
        result = self._call_api(messages, max_tokens=400, temperature=0.6) or "Unable to extract takeaways."
        self._cache[cache_key] = result
        return result

# Singleton instance
ai_service = AIService()