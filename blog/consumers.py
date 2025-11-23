import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class PostChatConsumer(AsyncWebsocketConsumer):
    """Real-time chat with RAG"""
   
    async def connect(self):
        self.post_slug = self.scope['url_route']['kwargs']['post_slug']
        self.room_group_name = f'post_chat_{self.post_slug}'
       
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
       
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to AI assistant with RAG. Ask anything!'
        }))
   
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
   
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            question = data.get('question', '').strip()
           
            if not question:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Question cannot be empty'
                }))
                return
           
            # Get post
            post = await self.get_post(self.post_slug)
           
            if not post:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Post not found'
                }))
                return
           
            # Generate AI answer
            answer = await self.get_ai_answer(question, post)
           
            # Send response
            await self.send(text_data=json.dumps({
                'type': 'ai_message',
                'question': question,
                'answer': answer
            }))
           
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error: {str(e)}'
            }))
   
    @database_sync_to_async
    def get_post(self, slug):
        from .models import Post
        try:
            return Post.objects.get(slug=slug, status='public')
        except Post.DoesNotExist:
            return None
   
    @database_sync_to_async
    def get_ai_answer(self, question, post):
        from .ai_services import ai_service
       
        question_lower = question.lower()
       
        # Special commands (examples; RAG handles general queries)
        if 'point by point' in question_lower or 'explain all' in question_lower:
            return ai_service.explain_point_by_point(post.body)
       
        elif 'study question' in question_lower or 'test question' in question_lower:
            num = 5
            for word in question.split():
                if word.isdigit():
                    num = int(word)
                    break
            return ai_service.generate_study_questions(post.body, num)
       
        elif 'key takeaway' in question_lower or 'main point' in question_lower:
            return ai_service.get_key_takeaways(post.body, 5)
       
        elif 'summarize' in question_lower or 'summary' in question_lower:
            num_lines = 3
            for word in question.split():
                if word.isdigit():
                    num_lines = min(int(word), 50)
                    break
            return ai_service.generate_summary(post.body, num_lines)
       
        # RAG for general questions
        else:
            chunks = post.content_chunks if post.content_chunks else ai_service.chunk_text(post.body)
            embeddings = post.get_embeddings()
           
            if embeddings is None and chunks:
                embeddings = ai_service.create_embeddings(chunks)
                if embeddings is not None:
                    post.save_embeddings(embeddings)
                    post.save(update_fields=['embeddings_json'])
           
            return ai_service.answer_with_rag(question, post.title, chunks, embeddings)