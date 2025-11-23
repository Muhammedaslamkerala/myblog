from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import F
from django.contrib import messages
import json
from ..models import Post, Comment
from ..ai_services import ai_service

@require_POST
def chat_with_post(request):
    """Fallback HTTP endpoint for chat"""
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        post_slug = data.get('post_slug', '')
       
        if not question:
            return JsonResponse({'success': False, 'error': 'Question required'}, status=400)
       
        post = get_object_or_404(Post, slug=post_slug, status='public')
       
        question_lower = question.lower()
       
        # Special commands
        if 'point by point' in question_lower or 'explain all' in question_lower:
            answer = ai_service.explain_point_by_point(post.body)
       
        elif 'study question' in question_lower or 'test question' in question_lower:
            num = 5
            for word in question.split():
                if word.isdigit():
                    num = int(word)
                    break
            answer = ai_service.generate_study_questions(post.body, num)
       
        elif 'key takeaway' in question_lower or 'main point' in question_lower:
            answer = ai_service.get_key_takeaways(post.body, 5)
       
        elif 'summarize' in question_lower or 'summary' in question_lower:
            num_lines = 3
            for word in question.split():
                if word.isdigit():
                    num_lines = min(int(word), 50)
                    break
            answer = ai_service.generate_summary(post.body, num_lines)
       
        # RAG for general
        else:
            chunks = post.content_chunks if post.content_chunks else ai_service.chunk_text(post.body)
            embeddings = post.get_embeddings()
           
            if embeddings is None and chunks:
                embeddings = ai_service.create_embeddings(chunks)
                if embeddings is not None:
                    post.save_embeddings(embeddings)
                    post.save(update_fields=['embeddings_json'])
           
            answer = ai_service.answer_with_rag(question, post.title, chunks, embeddings)
       
        return JsonResponse({'success': True, 'answer': answer})
       
    except Post.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Post not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Internal error: {str(e)}'}, status=500)