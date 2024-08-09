from django.contrib import admin
from .models import Item, APIToken


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('sku', 'brand', 'part_name',
                    'status', 'stock', 'updated_at')
    search_fields = ('sku', 'brand', 'part_name')
    list_filter = ('status', 'brand', 'created_at')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = ('token_type', 'created_at', 'updated_at')
    search_fields = ('token_type',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
