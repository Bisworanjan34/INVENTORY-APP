from django.contrib import admin

# Register your models here.
from .models import Product, BillItem, Bill

admin.site.register(Product)
admin.site.register(BillItem)
admin.site.register(Bill)
