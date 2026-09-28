from django.db import models
from accounts.models import User
import re

# Create your models here.
class Subject(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to="courses/", blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    subjects = models.ManyToManyField(
        Subject, through="CourseDetails", related_name="courses"
    )

    def __str__(self):
        return self.name


class CourseDetails(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.course.name} - {self.subject.name}"

class Lesson(models.Model):
    subject = models.ForeignKey(Subject,
    on_delete=models.CASCADE)
    lesson_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    link = models.URLField()

    def __str__(self):
        return self.lesson_name
    @property
    def embed_link(self):
        if not self.link:
            return ""

        patterns = [
            r"(?:youtube\.com/watch\?v=)([\w-]+)",
            r"(?:youtube\.com/shorts/)([\w-]+)",
            r"(?:youtu\.be/)([\w-]+)",
            r"(?:youtube\.com/embed/)([\w-]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, self.link)

            if match:
                video_id = match.group(1)

                return f"https://www.youtube.com/embed/{video_id}"

        return self.link
    
class LessonProgress(models.Model):
    student = models.ForeignKey(User,on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson,on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ("student", "lesson")
    def __str__(self):
        return f"{self.student.name} - {self.lesson.lesson_name}"

class Quiz(models.Model):
    subject = models.ForeignKey(Subject, 
    on_delete=models.CASCADE)
    quiz_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    passing_score = models.IntegerField()
    question_pdf = models.FileField(
        upload_to="quiz_questions/"
    )
    def __str__(self):
        return self.quiz_name


class QuizSubmission(models.Model):

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="submissions"
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="quiz_submissions"
    )

    question_pdf = models.FileField(
        upload_to="quiz/questions/"
    )

    answer_pdf = models.FileField(
        upload_to="quiz/answers/"
    )

    score = models.IntegerField(
        null=True,
        blank=True
    )

    graded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="graded_quiz_submissions",
        limit_choices_to={"role": "teacher"}
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.student.name} - {self.quiz.quiz_name}"

class Assignment(models.Model):
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )
    assignment_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    passing_score = models.IntegerField()
    question_pdf = models.FileField(
        upload_to="assignment_questions/"
    )
    def __str__(self):
        return self.assignment_name


class AssignmentSubmission(models.Model):

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions"
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assignment_submissions"
    )

    question_pdf = models.FileField(
        upload_to="assignments/questions/"
    )

    answer_pdf = models.FileField(
        upload_to="assignments/answers/"
    )

    score = models.IntegerField(
        null=True,
        blank=True
    )

    graded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="graded_assignment_submissions",
        limit_choices_to={"role": "teacher"}
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.student.name} - {self.assignment.assignment_name}"

class Payment(models.Model):

    PAYMENT_TYPE_CHOICES = [
        ("kbz_pay", "KBZ Pay"),
        ("wave_money", "Wave Money"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "student"},
        related_name="payments"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="payments"
    )
    payment_type = models.CharField(
        max_length=30,
        choices=PAYMENT_TYPE_CHOICES
    )

    transaction_id = models.CharField(
        max_length=100
    )

    receipt_image = models.ImageField(
        upload_to="payment_receipts/",
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    def __str__(self):
        return f"{self.student.name} - {self.course.name}"

class StudentEnrollment(models.Model):

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "student"},
        related_name="enrollments"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )

    enroll_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.name} - {self.course.name}"

class TeacherEnrollment(models.Model):

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "teacher"},
        related_name="teacher_enrollments"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="teacher_enrollments"
    )

    enroll_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.teacher.name} - {self.subject.name}"

        
class Certificate(models.Model):

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "student"},
        related_name="certificates"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="certificates"
    )

    issued_date = models.DateField()

    certificate_file = models.FileField(
        upload_to="certificates/",
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.student.name} - {self.course.name}"