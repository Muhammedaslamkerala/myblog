from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify


User = get_user_model()

class Series(models.Model):
    """A collection of posts created by a user."""
    title = models.CharField(max_length=200, verbose_name=_("Series Title"))
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='series')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('author', 'title')
        verbose_name = _("Series")
        verbose_name_plural = _("Series")
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.author.username}-{self.title}")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:series_detail', kwargs={'slug': self.slug})