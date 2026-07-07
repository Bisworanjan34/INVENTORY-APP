import os
import time
import base64
import re
import requests
import json
import datetime
from groq import Groq
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import F, Sum

from config import settings
from .models import Product, Bill, BillItem
from .forms import BillUploadForm
from fuzzywuzzy import process
from io import BytesIO
from django.core.files.base import ContentFile
from dotenv import load_dotenv
import gc
from PIL import Image
from django.contrib.sites.shortcuts import get_current_site

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def scan_and_analyze(bill_instance):
    try:
        if settings.DEBUG:
            img_path = bill_instance.bill_image.path
            img = Image.open(img_path)
        else:
            # Production ke liye jo code humne upar likha tha (requests wala)
            image_url = bill_instance.bill_image.url
            if not image_url.startswith("http"):
                # Agar relative path hai, toh domain jodein
                image_url = f"https://nandu-inventory.onrender.com{image_url}"
            print(
                f"DEBUG: Fetching image from: {image_url}"
            )  # Logs mein check karne ke liye
            img_response = requests.get(image_url, timeout=10)
            img_response.raise_for_status()  # Agar error ho toh turant pata chale
            img = Image.open(BytesIO(img_response.content))
        # Resize for API efficiency
        if img.size[0] > 1024 or img.size[1] > 1024:
            img.thumbnail((1024, 1024))

        # Temporary buffer mein save karein for OCR
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)

        # 2. OCR Execution
        api_key = os.getenv("OCR_API_KEY")
        response = requests.post(
            "https://api.ocr.space/parse/image",
            files={"file": ("bill.jpg", buffer, "image/jpeg")},
            data={"apikey": api_key, "language": "eng", "OCREngine": "2"},
        )

        result = response.json()
        print(f"DEBUG: OCR Result: {result}")
        if "ParsedResults" not in result or not result["ParsedResults"]:
            return []
        raw_text = result["ParsedResults"][0].get("ParsedText", "")

        # 3. AI Analysis (Llama 3.3)
        prompt = f"""Extract line items and total amount.
        1. Ignore tax, discount, or sub-totals if they are not the final amount.
        2. The 'total_amount' must be the final amount paid by the customer.
        3. Return the output in valid JSON format only.
        4. Ignore '$' or symbols, take only numeric values. 
        Output JSON: {{"items": [{{"name": "...", "qty": 0, "price": 0.0}}], "total_amount": 0.00}}. 
        Text: {raw_text}"""

        ai_response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )

        content = ai_response.choices[0].message.content
        json_match = re.search(r"\{.*\}", content, re.DOTALL)

        if not json_match:
            return []

        data = json.loads(json_match.group())
        items = data.get("items", [])
        total_amount = float(data.get("total_amount", 0))

        # Save to Model
        bill_instance.total_amount = total_amount
        bill_instance.save(update_fields=["total_amount"])

        # 4. Item Matching (Optimized)
        products = list(Product.objects.all())
        product_names = [p.name.lower() for p in products]
        found = []

        for item in items:
            name = str(item.get("name", "Unknown")).strip()
            qty = int(item.get("qty", 0))
            price = float(item.get("price", 0.0))

            if product_names:
                best = process.extractOne(name.lower(), product_names)
                if best and best[1] > 85:
                    p = next(p for p in products if p.name.lower() == best[0])
                    found.append(
                        {
                            "id": p.id,
                            "name": p.name,
                            "qty": qty,
                            "price": price,
                            "action": "update",
                        }
                    )
                else:
                    found.append(
                        {
                            "id": "new",
                            "name": name,
                            "qty": qty,
                            "price": price,
                            "action": "create",
                        }
                    )
            else:
                found.append(
                    {
                        "id": "new",
                        "name": name,
                        "qty": qty,
                        "price": price,
                        "action": "create",
                    }
                )

        return found

    except Exception as e:
        print(f"Scan Error: {e}")
        return []
    finally:
        gc.collect()


@login_required
def upload_bill_view(request):
    if request.method == "POST":
        form = BillUploadForm(request.POST, request.FILES)
        if form.is_valid():
            bill_id = request.session.get("current_bill_id")
            if bill_id:
                try:
                    bill = Bill.objects.get(id=bill_id)
                    bill.bill_image = request.FILES.get("bill_image", bill.bill_image)
                    bill.save()
                except Bill.DoesNotExist:
                    bill = form.save(commit=False)
                    bill.uploaded_by = request.user
                    bill.save()
            else:
                bill = form.save(commit=False)
                bill.uploaded_by = request.user
                bill.save()
                request.session["current_bill_id"] = bill.id

            results = scan_and_analyze(bill)
            request.session["scan_results"] = results
            return redirect("inventory:review_scan")
    else:
        form = BillUploadForm()
    return render(request, "inventory/upload.html", {"form": form})


@login_required
def confirm_update_view(request):
    if request.method == "POST":
        bill_id = request.session.get("current_bill_id")
        if not bill_id:
            return redirect("inventory:upload_page")

        bill = Bill.objects.get(id=bill_id)
        final_total = float(request.POST.get("final_total", 0))

        # Hum item delete nahi kar rahe, bas purani list ko ignore karke
        # UI mein dikh rahe items ko process kar rahe hain
        i = 0
        while f"name_{i}" in request.POST:
            name = request.POST.get(f"name_{i}")
            qty = float(request.POST.get(f"qty_{i}", 0))
            price = float(request.POST.get(f"price_{i}", 0))
            action = request.POST.get(f"action_{i}", "create")

            product = Product.objects.filter(name__iexact=name).first()

            if product:
                product.quantity += qty
                product.buying_price = price
                product.save()
            else:
                product = Product.objects.create(
                    name=name,
                    quantity=qty,
                    buying_price=price,
                    selling_price=price * 1.2,
                )

            # BillItem create karo (History maintain hogi)
            BillItem.objects.create(
                bill=bill, product=product, quantity=qty, price_at_purchase=price
            )
            i += 1

        bill.total_amount = final_total
        bill.save(update_fields=["total_amount"])

        # Cleanup
        request.session.pop("current_bill_id", None)
        request.session.pop("scan_results", None)

        messages.success(request, f"Bill finalized! Total: ₹{final_total:.2f}")
        return redirect("core:home")

    return redirect("inventory:upload_page")

    # return redirect("inventory:review_scan")


@user_passes_test(lambda u: u.is_superuser)
@login_required
def monthly_report_view(request):
    selected_month = int(request.GET.get("month", datetime.date.today().month))
    selected_year = int(request.GET.get("year", datetime.date.today().year))

    # Filter: Sirf confirmed bills dikhao (jinka amount > 0 ho)
    bills = Bill.objects.filter(
        upload_date__month=selected_month,
        upload_date__year=selected_year,
        total_amount__gt=0,
    ).order_by("-upload_date")

    total_amount = bills.aggregate(total=Sum("total_amount"))["total"] or 0

    return render(
        request,
        "inventory/report.html",
        {
            "bills": bills,
            "total_amount": total_amount,
            "selected_month": selected_month,
            "selected_year": selected_year,
        },
    )


@login_required
def view_stock_view(request):
    products = Product.objects.all()
    grand_total = (
        products.aggregate(total=Sum(F("buying_price") * F("quantity")))["total"] or 0
    )
    return render(
        request,
        "inventory/view_stock.html",
        {
            "products": products,
            "is_admin": request.user.is_superuser,
            "grand_total": grand_total,
        },
    )


@login_required
def review_scan_view(request):
    bill_id = request.session.get("current_bill_id")
    bill = Bill.objects.get(id=bill_id)
    results = request.session.get("scan_results", [])

    return render(
        request,
        "inventory/review.html",
        {
            "results": results,
            "bill": bill,  # <--- Ye 'bill' object bhejna zaroori hai
        },
    )


@login_required
def bill_gallery_view(request):
    # Sirf wahi bills lo jisme image physically exist karti ho
    if request.user.is_superuser:
        bills = (
            Bill.objects.exclude(bill_image__isnull=True)
            .exclude(bill_image="")
            .order_by("-upload_date")
        )
    else:
        bills = (
            Bill.objects.filter(uploaded_by=request.user)
            .exclude(bill_image__isnull=True)
            .exclude(bill_image="")
            .order_by("-upload_date")
        )
    return render(request, "inventory/gallery.html", {"bills": bills})


@login_required
def bill_detail_view(request, bill_id):
    # Admin sab dekh sakta hai, user sirf apna
    if request.user.is_superuser:
        bill = Bill.objects.get(id=bill_id)
    else:
        bill = Bill.objects.get(id=bill_id, uploaded_by=request.user)

    return render(request, "inventory/detail.html", {"bill": bill})


@user_passes_test(lambda u: u.is_superuser)
@login_required
def delete_bills_view(request):
    if request.method == "POST":
        bill_ids = request.POST.getlist("bill_ids")
        if bill_ids:
            Bill.objects.filter(id__in=bill_ids).delete()
    return redirect("inventory:gallery")
