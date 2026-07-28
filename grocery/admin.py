from django.contrib import admin

# Register your models here.
from .models import Product
from .models import SupportInquiry


@admin.register(SupportInquiry)
class SupportInquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "created_at")
    search_fields = ("name", "phone")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock")
