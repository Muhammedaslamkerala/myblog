from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os

@csrf_exempt
def custom_image_upload(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    upload = request.FILES.get('upload')
    if not upload:
        return JsonResponse({'error': 'No file provided'}, status=400)

    file_path = default_storage.save(os.path.join('uploads', upload.name), ContentFile(upload.read()))
    file_url = default_storage.url(file_path)
    return JsonResponse({'url': file_url})
