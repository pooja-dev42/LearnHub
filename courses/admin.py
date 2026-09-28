from django.contrib import admin
from .models import Course, Subject, CourseDetails


# Register your models here.
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description", "created_at")
    search_fields = ("name",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "description", "created_at")
    search_fields = ("name",)


@admin.register(CourseDetails)
class CourseDetailsAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "subject")
    list_filter = ("course", "subject")
