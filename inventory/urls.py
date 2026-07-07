from django.urls import path
from .views import (
    bill_detail_view,
    bill_gallery_view,
    delete_bills_view,
    upload_bill_view,
    review_scan_view,
    confirm_update_view,
    view_stock_view,
    monthly_report_view,  # Ye function import karna mat bhoolna
)

app_name = "inventory"

urlpatterns = [
    path("scan/", upload_bill_view, name="upload_page"),
    path("review/", review_scan_view, name="review_scan"),
    path("confirm/", confirm_update_view, name="confirm_update"),
    path("stock/", view_stock_view, name="view_stock"),
    path("report/", monthly_report_view, name="report"),  # Yeh naya URL
    path("gallery/", bill_gallery_view, name="gallery"),
    path("bill/<int:bill_id>/", bill_detail_view, name="bill_detail"),
    path("delete-bills/", delete_bills_view, name="delete_bills"),
]
