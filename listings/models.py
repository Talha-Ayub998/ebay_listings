from django.db import models


class Item(models.Model):
    STATUS_CHOICES = [
        ('not listed', 'Not Listed'),
        ('listed', 'Listed'),
        ('error', 'Error'),
        ('updated', 'Updated for Price & Stock'),
    ]

    sku = models.CharField(max_length=255, unique=True)
    item_id = models.CharField(
        max_length=255, unique=True, blank=True, null=True)
    brand = models.CharField(max_length=255)
    part_name = models.CharField(max_length=255)
    partslink = models.CharField(max_length=255, blank=True, null=True)
    oem_number = models.CharField(max_length=255, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_revenue18 = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    handling_revenue18 = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)
    stock_va = models.IntegerField(blank=True, null=True)
    stock_il = models.IntegerField(blank=True, null=True)
    stock_las1 = models.IntegerField(blank=True, null=True)
    stock_peru = models.IntegerField(blank=True, null=True)
    stock_gpt = models.IntegerField(blank=True, null=True)
    stock_jax = models.IntegerField(blank=True, null=True)
    stock = models.IntegerField()
    image_url = models.URLField(blank=True, null=True)
    pdescription = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default='not listed')
    debug_info = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sku} - {self.item_id}"


class APIToken(models.Model):
    access_token = models.TextField()
    refresh_token = models.TextField()
    refresh_token_expires_in = models.IntegerField()
    token_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Token type: {self.token_type} (Created at: {self.created_at})"
