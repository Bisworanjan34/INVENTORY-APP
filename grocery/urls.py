from django.urls import path
from . import views

app_name = "grocery"

urlpatterns = [
    path("product-list/", views.grocery_list, name="grocery_list"),
    path("product-add/", views.add_product, name="add_product"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("product-update/<int:pk>/", views.update_product, name="update_product"),
    path("product-delete/<int:pk>/", views.delete_product, name="delete_product"),
    path("cart/", views.view_cart, name="view_cart"),
    path("add-to-cart/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path(
        "update-cart-ajax/<int:product_id>/<str:action>/",
        views.update_cart_ajax,
        name="update_cart_ajax",
    ),
    path(
        "remove-from-cart/<int:item_id>/",
        views.remove_from_cart,
        name="remove_from_cart",
    ),
    path("checkout/", views.checkout, name="checkout"),
    path("admin-orders/", views.admin_orders, name="admin_orders"),
    path("order-detail/<int:order_id>/", views.order_detail, name="order_detail"),
    path("delete-order/<int:order_id>/", views.delete_order, name="delete_order"),
    path(
        "delete-address/<int:address_id>/", views.delete_address, name="delete_address"
    ),
    path("save-new-address/", views.save_new_address, name="save_new_address"),
    path("buy-now/<int:product_id>/", views.buy_now, name="buy_now"),
    path("order-success/", views.order_success, name="order_success"),
    path("my-orders/", views.my_orders, name="my_orders"),
    path(
        "my-order-details/<int:order_id>/",
        views.my_order_details,
        name="my_order_details",
    ),
    path("profile/", views.profile_view, name="profile"),
    path("payment-method/", views.payment_method, name="payment_method"),
    path("process-order/", views.process_order, name="process_order"),
    path("upi-payment/", views.upi_payment, name="upi_payment"),
    path("confirm-upi/", views.confirm_upi_payment, name="confirm_upi_payment"),
    path('update-status/<int:order_id>/<str:status>/', views.update_order_status, name='update_status'),
]
