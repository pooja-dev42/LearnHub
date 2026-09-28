from django.urls import path
from . import views

urlpatterns = [
    path("", views.course_list, name="courses"),
    path(
    "course/<int:course_id>/",
    views.course_detail,
    name="course_detail"
),
    path(
    "course/<int:course_id>/payment/",
    views.payment,
    name="payment"
),
]
