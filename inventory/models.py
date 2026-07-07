from django.db import models
from django.contrib.auth.models import User


class Product(models.Model):
    name = models.CharField(max_length=200, unique=True)  # Unique hona zaroori hai
    quantity = models.IntegerField(default=0)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class Bill(models.Model):
    """
    Ek naya model jo har bill ka record rakhega.
    Isse aap profit/loss calculate kar sakte ho.
    """

    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    bill_image = models.ImageField(upload_to="bills/")
    upload_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        return f"Bill {self.id} - {self.uploaded_by.username}"


class BillItem(models.Model):
    """
    Har bill ke andar kitne items hain uska breakdown.
    """

    bill = models.ForeignKey(Bill, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class ProductAlias(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="aliases"
    )
    alias_name = models.CharField(max_length=200)

    def __str__(self):
        return self.alias_name
