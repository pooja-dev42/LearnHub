from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User
from .models import Course, Payment, TeacherEnrollment


# Create your views here.
def course_list(request):
    search = request.GET.get("search","").strip()
    courses = Course.objects.all()
    if search:
        courses = courses.filter(name__icontains=search)
    return render(request, "courses/course_list.html", {"courses": courses, "search": search,})


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    teacher_enrollment = ( TeacherEnrollment.objects.filter(subject__courses=course).select_related("teacher").first())
    teacher = teacher_enrollment.teacher if teacher_enrollment else None
    return render(request, "courses/course_detail.html", {"course": course, "teacher": teacher})


def payment(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        user_id = request.session.get("user_id")

        if not user_id:
            return redirect("login")

        student = get_object_or_404(User, id=user_id, role="student")

        # prevent duplicate payment
        existing_payment = Payment.objects.filter(
            student=student, course=course
        ).exists()

        if existing_payment:
            messages.warning(
                request, "You already submitted payment for this course."
            )
            return redirect("courses")

        payment_type = request.POST.get("payment_type")
        transaction_id = request.POST.get("transaction_id")
        receipt_image = request.FILES.get("receipt_image")

        Payment.objects.create(
            student=student,
            course=course,
            payment_type=payment_type,
            transaction_id=transaction_id,
            receipt_image=receipt_image,
            status="pending",
        )

        messages.success(
            request, "Payment submitted. Waiting for admin approval."
        )
        return redirect("courses")
    return render(request, "courses/payment.html", {"course": course})