from .models import CartItem


def cart_count(request):
    if request.user.is_authenticated:
        # Yahan hum saari quantities ka SUM nikal rahe hain
        count = CartItem.objects.filter(user=request.user).values_list(
            "quantity", flat=True
        )
        return {"cart_total_qty": sum(count)}
    return {"cart_total_qty": 0}
