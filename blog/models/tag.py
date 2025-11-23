from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Tag Name"))
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)