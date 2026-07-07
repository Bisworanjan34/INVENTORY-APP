import os
import time
import base64
import re
import json
import datetime
from groq import Groq
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import F, Sum
from django.conf import settings
from .models import Product, Bill, BillItem
from .forms import BillUploadForm
from fuzzywuzzy import process
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def scan_and_analyze(bill_instance):
    try:
        import easyocr

        reader = easyocr.Reader(["en"])
        result = reader.readtext(bill_instance.bill_image.path, detail=0)
        raw_text = " ".join(result)

        prompt = f"""
You are an expert accountant. You are provided with the text of a grocery bill or any food bill .
Your ONLY task is to extract the line items and the GRAND TOTAL amount which is match with final amount total price or total amount think smart remember one thing that total amount or total price always the last number in the bill bottom of the bill you can easily identify it try to get the accurate total amount ok.

Follow these strict rules:
1.if you see any of this symbols like $ before or after combine with total price or total amount then remove that symbol from numbers and take only numeric value of total and one more thing is always see the qty section and price section i mean that line details take not other section details apply in qty or price section only take price and qty section value in their sections.always remember that name in alphanumeric and price in numeric only and qty in numeric only and total amount in numeric only and before that check deeply then take a action like a pro .  
2. Ignore tax, discount, or sub-totals if they are not the final amount.
3. The 'total_amount' must be the final amount paid by the customer.
4. Return the output in valid JSON format only.
5. Output format: {{"items": [{{"name": "...", "qty": 0, "price": 0.0}}], "total_amount": 0.00}}

Bill Text: 
{raw_text}
"""

        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )

        content = response.choices[0].message.content
        # JSON extract karne ka behtar tarika
        json_match = re.search(r"\{.*\}", content, re.DOTALL)

        if not json_match:
            return []

        data = json.loads(json_match.group())
        items = data.get("items", [])
        total_amount = float(data.get("total_amount", 0))

        # 1. Total Amount ko Bill instance mein save karo
        bill_instance.total_amount = total_amount
        bill_instance.save(update_fields=["total_amount"])

        # 2. Items processing
        found = []
        products = Product.objects.all()
        names = [p.name.lower() for p in products]

        for item in items:
            name = str(item.get("name", "Unknown")).strip()
            qty = int(item.get("qty", 0))
            price = float(item.get("price", 0.0))

            best = process.extractOne(name.lower(), names) if names else None
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

        return found

    except Exception as e:
        print(f"Scan Error: {e}")
        return []


@login_required
def upload_bill_view(request):
    if request.method == "POST":
        form = BillUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Agar session mein pehle se koi bill id hai, toh use update karo
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

            # Scan and Analyze (Text model se)
            results = scan_and_analyze(bill)
            request.session["scan_results"] = results
            return redirect("inventory:review_scan")
    else:
        form = BillUploadForm()
    return render(request, "inventory/upload.html", {"form": form})


# --- Baaki saare functions waisay hi rahenge ---


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
