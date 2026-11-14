from django.contrib import admin

from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'written_on', 'published', 'featured', 'download_count')
    prepopulated_fields = {'slug': ('title',)}
