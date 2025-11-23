"""
URL configuration for main project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from ckeditor_custom.views import custom_image_upload

# Custom Error Handlers
handler404 = 'users.views.error_views.handler404'
handler500 = 'users.views.error_views.handler500'
handler403 = 'users.views.error_views.handler403'
handler400 = 'users.views.error_views.handler400'

urlpatterns = [
    path('admin/', admin.site.urls),
    path("ckeditor5/upload/", custom_image_upload, name="ckeditor_upload"),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
    path('account/', include(('users.urls', 'users'), namespace='users')),
    path('', include('blog.urls')),  # Root URLs
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
