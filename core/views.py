from django.utils import timezone

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm

from inventory.models import Bill
from .forms import UserRegistrationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.sessions.models import Session


# 1. Registration
def register_view(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            return redirect("core:login")
    else:
        form = UserRegistrationForm()
    return render(request, "auth/register.html", {"form": form})


# 2. Login
def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()

            # PRO FEATURE: Purane sessions ko khatam karein (Security Kick-out)
            # Isse ek user ek hi device par active rahega
            Session.objects.filter(expire_date__gte=timezone.now()).delete()

            login(request, user)

            # Success message for professional feedback
            messages.success(
                request, f"Welcome back, {user.username}! Securely logged in."
            )
            return redirect("core:home")
        else:
            # Error handling for invalid credentials
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()

    return render(request, "auth/login.html", {"form": form})


# 3. Logout
def logout_view(request):
    logout(request)
    return redirect("core:home")


# @login_required
def home_view(request):
    # Error Handling: Check if user is logged in
    if not request.user.is_authenticated:
        # Agar user login nahi hai, toh empty list bhejo taaki template crash na ho
        context = {
            "recent_bills": [],
            "bills": [],
        }
        return render(request, "core/home.html", context)

    # Agar user login hai, tabhi database queries chalengi
    if request.user.is_superuser:
        recent_bills = Bill.objects.all().order_by("-id")[:4]
        bills = Bill.objects.all().order_by("-id")
    else:
        recent_bills = Bill.objects.filter(uploaded_by=request.user).order_by("-id")[:4]
        bills = Bill.objects.filter(uploaded_by=request.user).order_by("-id")

    context = {
        "recent_bills": recent_bills,
        "bills": bills,
    }
    return render(request, "core/home.html", context)


# views.py


def error_404_view(request, exception):
    return render(request, "404.html", status=404)


def custom_500_view(request):
    return render(request, "500.html", status=500)
