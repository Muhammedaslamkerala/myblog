from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify


User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name=_("Category Name"))
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    color = models.CharField(max_length=7, default="#667eea", help_text="Hex color code")
    icon = models.CharField(max_length=50, blank=True, help_text="Bootstrap icon class")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
       
        if not self.slug or (self.pk is None and not self.slug): 
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
           
            while type(self).objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:category', kwargs={'slug': self.slug})