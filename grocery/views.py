from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import OrderItem, Product, CartItem, Order, SavedAddress, Profile
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction


@login_required
def grocery_list(request):
    query = request.GET.get("q")  # Search bar se input uthao
    products = Product.objects.all()

    if query:
        # Product name ya category mein search karega
        products = products.filter(name__icontains=query)

    return render(request, "grocery/list.html", {"products": products})


# --- PRODUCT CRUD (Admin Only) ---
@login_required
@user_passes_test(lambda u: u.is_superuser)
def add_product(request):
    if request.method == "POST":
        Product.objects.create(
            name=request.POST["name"],
            price=request.POST["price"],
            stock=request.POST["stock"],
            image=request.FILES.get("image"),
        )
        return redirect("grocery:grocery_list")
    return render(request, "grocery/manage.html", {"mode": "add"})


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "grocery/detail.html", {"product": product})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def update_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.name = request.POST.get("name")
        product.price = request.POST.get("price")
        product.stock = request.POST.get("stock")
        if request.FILES.get("image"):
            product.image = request.FILES.get("image")
        product.save()
        return redirect("grocery:grocery_list")
    return render(
        request, "grocery/manage.html", {"product": product, "mode": "update"}
    )


@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_product(request, pk):
    get_object_or_404(Product, pk=pk).delete()
    return redirect("grocery:grocery_list")


# --- CART FUNCTIONS ---
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user, product=product
    )
    if not created:
        if product.stock > cart_item.quantity:
            cart_item.quantity += 1
            cart_item.save()
    return redirect("grocery:view_cart")


@login_required
def update_cart_ajax(request, product_id, action):
    product = get_object_or_404(Product, id=product_id)
    cart_item = get_object_or_404(CartItem, user=request.user, product=product)

    if action == "increase":
        if product.stock > cart_item.quantity:
            cart_item.quantity += 1
            cart_item.save()
    elif action == "decrease":
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
            return JsonResponse({"status": "removed"})

    return JsonResponse({"status": "success", "qty": cart_item.quantity})


@login_required
def view_cart(request):
    items = CartItem.objects.filter(user=request.user)
    total = sum(item.product.price * item.quantity for item in items)
    return render(request, "grocery/cart.html", {"items": items, "total": total})


@login_required
def remove_from_cart(request, item_id):
    get_object_or_404(CartItem, id=item_id, user=request.user).delete()
    return redirect("grocery:view_cart")


@login_required
def order_success(request):
    return render(request, "grocery/order_success.html")


@login_required
def checkout(request):
    if request.method == "POST":
        # 1, 2, 3: Address Save/Delete/Edit logic wahi rahega...
        if "save_address" in request.POST:
            SavedAddress.objects.create(
                user=request.user,
                full_name=request.POST.get("name"),
                phone=request.POST.get("phone"),
                address=request.POST.get("address"),
            )
            return redirect("grocery:checkout")
        elif "delete_address" in request.POST:
            SavedAddress.objects.filter(
                id=request.POST.get("delete_address"), user=request.user
            ).delete()
            return redirect("grocery:checkout")
        elif "edit_address" in request.POST:
            addr = get_object_or_404(
                SavedAddress, id=request.POST.get("address_id"), user=request.user
            )
            addr.full_name = request.POST.get("edit_name")
            addr.phone = request.POST.get("edit_phone")
            addr.address = request.POST.get("edit_address")
            addr.save()
            return redirect("grocery:checkout")

        # 4. PLACE ORDER -> Redirect to Payment Method
        elif "place_order" in request.POST:
            address_id = request.POST.get("selected_address_id")
            if not address_id:
                messages.error(request, "Select an address first!")
                return redirect("grocery:checkout")
            # Address ID session mein store kar rahe hain
            request.session["selected_address_id"] = address_id
            return redirect("grocery:payment_method")

    return render(
        request,
        "grocery/checkout.html",
        {
            "saved_addresses": SavedAddress.objects.filter(user=request.user),
            "cart_items": CartItem.objects.filter(user=request.user),
            "grand_total": sum(
                i.product.price * i.quantity
                for i in CartItem.objects.filter(user=request.user)
            ),
        },
    )


@login_required
def buy_now(request, product_id):
    try:
        product = get_object_or_404(Product, id=product_id)

        # Cart clear karna
        CartItem.objects.filter(user=request.user).delete()

        # Naya item add karna
        CartItem.objects.create(user=request.user, product=product, quantity=1)

        # Yahan message ki zaroorat nahi hai kyunki seedha checkout pe ja rahe hain
        return redirect("grocery:checkout")

    except Exception as e:
        # Agar error aaye tabhi message dikhao
        messages.error(request, "err products loading time please try again ?")
        return redirect("grocery:grocery_list")


@login_required
@user_passes_test(lambda u: u.is_superuser)
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "grocery/order_detail.html", {"order": order})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_orders(request):
    orders = Order.objects.all().order_by("-created_at")
    return render(request, "grocery/admin_orders.html", {"orders": orders})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def delete_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order.delete()
    return redirect(
        "grocery:admin_orders"
    )  # Delete hone ke baad wapas dashboard pe bhejo


@login_required
def save_new_address(request):
    if request.method == "POST":
        SavedAddress.objects.create(
            user=request.user,
            full_name=request.POST.get("name"),
            phone=request.POST.get("phone"),
            address=request.POST.get("address"),
        )
    return redirect("grocery:checkout")


@login_required
def delete_address(request, address_id):
    address = get_object_or_404(SavedAddress, id=address_id, user=request.user)
    address.delete()
    return redirect("grocery:checkout")  # Wapas checkout pe bhej do


@login_required
def my_orders(request):
    # Sirf login user ke orders filter karo
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "grocery/my_orders.html", {"orders": orders})


@login_required
def my_order_details(request, order_id):
    # Sirf login user ka hi order check karein (Security)
    order = get_object_or_404(Order, id=order_id, user=request.user)
    items = OrderItem.objects.filter(order=order)

    return render(
        request, "grocery/my_order_details.html", {"order": order, "items": items}
    )


# profile sections
@login_required
def profile_view(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    if request.method == "POST":
        try:
            profile.name = request.POST.get("name", "").strip()
            profile.bio = request.POST.get("bio", "").strip()

            if request.FILES.get("photo"):
                profile.photo = request.FILES.get("photo")

            profile.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("grocery:profile")
        except Exception as e:
            messages.error(request, f"Error updating profile: {str(e)}")

    return render(request, "grocery/profile.html", {"profile": profile})


# payment system fucntions
@login_required
def payment_method(request):
    return render(request, "grocery/payment_method.html")


def create_final_order(request, method, status):
    address_id = request.session.get("selected_address_id")
    cart_items = CartItem.objects.filter(user=request.user)

    try:
        with transaction.atomic():
            addr = SavedAddress.objects.get(id=address_id, user=request.user)
            total = sum(i.product.price * i.quantity for i in cart_items)

            order = Order.objects.create(
                user=request.user,
                full_name=addr.full_name,
                phone=addr.phone,
                address=addr.address,
                total_price=total,
                payment_method=method,
                payment_status=status,
            )
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_name=item.product.name,
                    price=item.product.price,
                    quantity=item.quantity,
                    image_url=item.product.image.url,
                )
            cart_items.delete()
        return redirect("grocery:order_success")
    except Exception as e:
        messages.error(request, "Order failed.")
        return redirect("grocery:checkout")


@login_required
def process_order(request):
    if request.method == "POST":
        method = request.POST.get("pay_method")  # 'COD' or 'ONLINE'
        address_id = request.session.get("selected_address_id")
        cart_items = CartItem.objects.filter(user=request.user)

        if not address_id or not cart_items.exists():
            return redirect("grocery:checkout")

        # 1. COD hai toh seedha 'Confirmed' status de do
        # Kyunki COD mein payment delivery pe hogi, so admin ko verification ki zarurat nahi
        if method == "COD":
            return create_final_order(request, method, "Confirmed")

        # 2. ONLINE hai toh pehle payment page par bhejo
        elif method == "ONLINE":
            return redirect("grocery:upi_payment")

    return redirect("grocery:checkout")


@login_required
def confirm_upi_payment(request):
    if request.method == "POST":
        # User ne "I have paid" dabaya hai, isliye order create karo as 'Pending'
        # Admin manually verify karke ise 'Confirmed' ya 'Cancelled' karega
        return create_final_order(request, "ONLINE", "Pending")
    return redirect("grocery:checkout")


@login_required
def upi_payment(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(i.product.price * i.quantity for i in cart_items)
    return render(request, "grocery/upi_payment.html", {"grand_total": total})


@login_required
@user_passes_test(lambda u: u.is_superuser)
# views.py (Admin update function)
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == "POST":
        order.payment_status = request.POST.get("status")
        # Agar status Cancelled hai, toh reason bhi save karo
        if order.payment_status == "Cancelled":
            order.cancellation_reason = request.POST.get("reason")
        order.save()
        return redirect("grocery:admin_orders")
