"""
Celery tasks for async processing.
Updated: generate_tags_task and suggest_category_task now use post.summary instead of post.body
for efficiency with large posts. Falls back to body[:2000] if summary is missing/empty.
This leverages the concise AI-generated summary for better, faster AI processing.
"""

from celery import shared_task
from django.apps import apps
import logging
from django.db import transaction
from .models import Post  
from .ai_services import ai_service
import json
import numpy as np
from typing import Dict, Any
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def generate_tags_task(self, post_id):
    """Generate tags asynchronously using post summary"""
    try:
        Post = apps.get_model('blog', 'Post')
        Tag = apps.get_model('blog', 'Tag')
        post = Post.objects.get(id=post_id)
       
        from .ai_services import ai_service
        
        # Use summary for efficiency; fallback to body excerpt
        content_for_tags = post.summary if post.summary else strip_tags(post.body)[:2000]
        
        if not content_for_tags.strip():
            logger.warning(f"Post {post_id} has no text content for tag generation")
            return {'success': False, 'error': 'No text content'}
        
        tag_names = ai_service.generate_tags(post.title, content_for_tags)
       
        if tag_names:
            for tag_name in tag_names:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                post.tags.add(tag)
           
            post.ai_generated_tags = True
            post.save(update_fields=['ai_generated_tags'])
            logger.info(f"Generated tags for post {post.title}: {tag_names}")
            return {'success': True, 'tags': tag_names}
        else:
            logger.warning(f"No tags generated for post {post_id}")
            return {'success': False, 'error': 'No tags generated'}
           
    except Post.DoesNotExist:
        logger.error(f"Post {post_id} does not exist")
        return {'success': False, 'error': 'Post not found'}
    except Exception as e:
        logger.error(f"Tag generation error for post {post_id}: {e}")
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, max_retries=3)
def suggest_category_task(self, post_id):
    """Suggest category asynchronously using post summary"""
    try:
        Post = apps.get_model('blog', 'Post')
        Category = apps.get_model('blog', 'Category')
       
        post = Post.objects.get(id=post_id)
        categories = Category.objects.filter(is_active=True)
       
        if not categories.exists():
            logger.warning("No active categories available")
            return {'success': False, 'error': 'No categories'}
       
        from .ai_services import ai_service
        
        # Use summary for efficiency; fallback to body excerpt
        content_for_category = post.summary if post.summary else strip_tags(post.body)[:2000]
        
        if not content_for_category.strip():
            logger.warning(f"Post {post_id} has no text content for category suggestion")
            return {'success': False, 'error': 'No text content'}
        
        category = ai_service.suggest_category(post.title, content_for_category, categories)
       
        if category:
            post.categories.add(category)
            post.ai_generated_category = True
            post.save(update_fields=['ai_generated_category'])
            logger.info(f"Suggested category for post {post.title}: {category.name}")
            return {'success': True, 'category': category.name}
        else:
            logger.warning(f"No category suggested for post {post_id}")
            return {'success': False, 'error': 'No category suggested'}
           
    except Post.DoesNotExist:
        logger.error(f"Post {post_id} does not exist")
        return {'success': False, 'error': 'Post not found'}
    except Exception as e:
        logger.error(f"Category suggestion error for post {post_id}: {e}")
        raise self.retry(exc=e, countdown=60)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def prepare_rag_data_task(self, post_id: str) -> Dict[str, Any]:
    """
    Celery task to generate embeddings for a blog post.
    Handles errors and retries gracefully.
    """
    try:
        with transaction.atomic():
            post = Post.objects.select_for_update().get(id=post_id)
            
            # Skip if already processed
            if post.embeddings_json:
                logger.info(f"Post {post_id} already has embeddings.")
                return {'success': True, 'message': 'Already processed'}
            
            # Get clean text content
            clean_body = strip_tags(post.body).strip()
            
            if not clean_body:
                logger.warning(f"Post {post_id} has no text content for RAG")
                return {'success': False, 'error': 'No text content'}
            
            # Chunk the content
            chunks = ai_service.chunk_text(clean_body)
            if not chunks:
                raise ValueError("No chunks generated from content.")
            
            # Generate embeddings (FIX: Pass tuple for caching)
            embeddings = ai_service.create_embeddings(tuple(chunks))
            if embeddings is None:
                raise ValueError("Failed to generate embeddings.")
            
            # Store in DB
            post.content_chunks = chunks
            post.embeddings_json = json.dumps(embeddings.tolist())
            post.save(update_fields=['content_chunks', 'embeddings_json'])
            
            logger.info(f"Successfully processed RAG data for post: {post.title[:50]}")
            return {
                'success': True, 
                'post_id': str(post_id), 
                'num_chunks': len(chunks)
            }
    
    except Post.DoesNotExist:
        logger.error(f"Post {post_id} does not exist")
        return {'success': False, 'error': 'Post not found'}
    except Exception as exc:
        logger.error(f"RAG preparation error for post {post_id}: {exc}")
        # Retry on non-permanent errors
        raise self.retry(exc=exc)
