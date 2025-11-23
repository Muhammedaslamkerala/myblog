from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify
from django.utils.html import strip_tags
from django.utils import timezone
from django.db.models import Q
import uuid
import json
import numpy as np
from .category import Category
from .tag import Tag
from .series import Series

User = get_user_model()

class PostManager(models.Manager):
    def public(self):
        return self.filter(status='public')

    def drafts(self):
        return self.filter(status='draft')

    def featured(self):
        return self.filter(is_featured=True, status='public')

    def private(self):
        return self.filter(status='private')

class Post(models.Model):
    STATUS_CHOICES = [
        ('public', 'Public'),
        ('private', 'Private'),
        ('draft', 'Draft'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt = models.TextField(max_length=300, blank=True, verbose_name=_("Excerpt"))
    summary = models.TextField(blank=True, editable=False, verbose_name=_("Summary"))
    body = CKEditor5Field(verbose_name=_("Body"), config_name='default')
    featured_image = models.ImageField(upload_to='post_images/%Y/%m/%d/', blank=True, null=True, verbose_name=_("Featured Image"))
    word_count = models.PositiveIntegerField(default=0, editable=False)

    # Status and publishing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_published = models.BooleanField(default=True, verbose_name=("Is Published"))
    is_featured = models.BooleanField(default=False, verbose_name=_("Is Feactured"))
    published_date = models.DateTimeField(blank=True, null=True, verbose_name=_("Published Date"))

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    last_modified = models.DateTimeField(auto_now=True, verbose_name=_("Last Modified"))

    # Relationships
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("Author"),
        related_name='posts',
        default=1
    )
    categories = models.ManyToManyField(
        Category,
        related_name='posts',
        verbose_name=_("Categories"),
        blank=True
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='posts',
        verbose_name=_("Tags"),
        blank=True
    )
    series = models.ForeignKey(
        Series,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name=_("Series"),
        help_text=_("The series this post belongs to, if any.")
    )

    # Engagement
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    bookmarks_count = models.PositiveIntegerField(default=0)
    order_in_series = models.PositiveIntegerField(default=0)

    # Settings
    allow_comments = models.BooleanField(default=True, verbose_name=_("Allow Comments"))
    meta_description = models.TextField(max_length=160, blank=True)

    # AI-generated fields
    ai_generated_tags = models.BooleanField(default=False)
    ai_generated_category = models.BooleanField(default=False)

    # RAG fields
    content_chunks = models.JSONField(default=list, blank=True)
    embeddings_json = models.TextField(blank=True, null=True)  # Store as JSON string

    objects = PostManager()

    class Meta:
        verbose_name = _("Post")
        verbose_name_plural = _("Posts")
        ordering = ['-published_date', '-created_at']

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        # Track the original status if the object already exists
        original_status = None
        if not self._state.adding:
            original_status = Post.objects.get(pk=self.pk).status

        # Set published_date ONLY when status changes from a non-published state to 'public'
        if self.status == 'public' and original_status != 'public':
            self.published_date = timezone.now()

        # Generate unique slug
        if not self.slug or self.__class__.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while self.__class__.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Calculate word count and generate excerpt
        clean_body = strip_tags(self.body)
        self.word_count = len(clean_body.split())
        if not self.excerpt:
            self.excerpt = (clean_body[:250] + "..." if len(clean_body) > 250 else clean_body)

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:post_details', kwargs={'slug': self.slug})

    def get_reading_time(self):
        return max(1, round(self.word_count / 200))

    def get_related_posts(self):
        """Get related posts based on categories and tags"""
        return Post.objects.public().filter(
            Q(categories__in=self.categories.all()) |
            Q(tags__in=self.tags.all())
        ).exclude(id=self.id).distinct()[:3]

    def save_embeddings(self, embeddings):
        '''Save embeddings as JSON'''
        if embeddings is not None:
            self.embeddings_json = json.dumps(embeddings.tolist())

    def get_embeddings(self):
        '''Load embeddings from JSON'''
        if self.embeddings_json:
            return np.array(json.loads(self.embeddings_json))
        return None

    def prepare_rag_data(self):
        '''Prepare chunks and embeddings for RAG'''
        from blog.ai_services import ai_service


        # Create chunks
        chunks = ai_service.chunk_text(self.body)
        self.content_chunks = chunks

        # Create embeddings
        embeddings = ai_service.create_embeddings(chunks)
        if embeddings is not None:
            self.save_embeddings(embeddings)

        self.save(update_fields=['content_chunks', 'embeddings_json'])