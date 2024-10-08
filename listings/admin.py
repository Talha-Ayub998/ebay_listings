from django.contrib import admin
from .models import Item, APIToken, S3File


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('sku', 'brand', 'item_id',
                    'status', 'stock', 'updated_at')
    search_fields = ('sku', 'brand', 'item_id')
    list_filter = ('status', 'brand', 'created_at')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = ('token_type', 'created_at', 'updated_at')
    search_fields = ('token_type',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(S3File)
class S3FileAdmin(admin.ModelAdmin):
    list_display = ('name', 'file_hash', 'upload_time')
    search_fields = ('name', 'file_hash')
    ordering = ('-upload_time',)
    readonly_fields = ('upload_time',)
