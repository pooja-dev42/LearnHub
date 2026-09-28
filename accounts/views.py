from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .models import User


def register(request):

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone")

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("register")

        # Create student account
        User.objects.create(
            name=name,
            email=email,
            password=make_password(password),
            phone=phone,
            role="student"
        )

        messages.success(request, "Account created successfully. Please login.")

        return redirect("login")

    return render(request, "accounts/register.html")


def login_view(request):

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("role")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Invalid email or password.")
            return redirect("login")
        # Check password
        if not check_password(password, user.password):
            messages.error(request, "Invalid email or password.")
            return redirect("login")

        # Check selected role
        if user.role != role:
            messages.error(
                request,
                "The selected role does not match your account."
            )
            return redirect("login")

         # Save user information in session
        request.session["user_id"] = user.id
        request.session["name"] = user.name
        request.session["role"] = user.role

        # Redirect according to role
        if user.role == "student":
            return redirect("student_dashboard")

        elif user.role == "teacher":
            return redirect("teacher_dashboard")

        elif user.role == "admin":
            return redirect("admin_dashboard")

    return render(request, "accounts/login.html")

def logout_view(request):

    request.session.flush()

    return redirect("login")

