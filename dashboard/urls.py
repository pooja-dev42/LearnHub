from django.urls import path
from . import views

urlpatterns = [
    # Student
    path("student/", views.student_dashboard, name="student_dashboard"),
    path("student/my-courses/", views.my_courses, name="my_courses"),
    path(
        "student/course/<int:course_id>/learn/",
        views.course_learning,
        name="course_learning",
    ),
    path("student/quizzes/", views.quiz, name="quiz"),
    path(
        "student/quiz/<int:quiz_id>/",
        views.quiz_detail,
        name="quiz_detail",
    ),
    path("student/assignment/", views.assignment, name="assignment"),
    path(
        "student/assignment/<int:assignment_id>/",
        views.assignment_detail,
        name="assignment_detail",
    ),
    path("student/grades/", views.grades, name="grades"),
    path("student/certificates/", views.certificates, name="certificates"),
    path(
        "student/student_profile/",
        views.student_profile,
        name="student_profile",
    ),

    # Teacher
    path(
        "teacher/teacher_profile/",
        views.teacher_profile,
        name="teacher_profile",
    ),
    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path(
        "teacher/subjects/",
        views.teacher_subjects,
        name="teacher_subjects",
    ),
    path(
        "teacher/quiz-submissions/",
        views.teacher_quiz_submissions,
        name="teacher_quiz_submissions",
    ),
    path(
        "teacher/quiz-submission/<int:submission_id>/",
        views.teacher_quiz_submission_detail,
        name="teacher_quiz_submission_detail",
    ),
    path(
        "teacher/assignment-submissions/",
        views.teacher_assignment_submissions,
        name="teacher_assignment_submissions",
    ),
    path(
        "teacher/assignment-submission-detail/<int:submission_id>/",
        views.teacher_assignment_submission_detail,
        name="teacher_assignment_submission_detail",
    ),
    path(
        "teacher/grades/",
        views.teacher_grades,
        name="teacher_grades",
    ),

    # Admin
    path("admin/profile/", views.profile, name="profile"),
    path("admin_dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Students
    path(
        "admin/admin-students/",
        views.admin_students,
        name="admin_students",
    ),
    path(
        "admin-student-grades/",
        views.admin_student_grades,
        name="admin_student_grades",
    ),
    path(
        "admin/quiz-submissions/",
        views.admin_quiz_submissions,
        name="admin_quiz_submissions",
    ),
    path(
        "admin/assignment-submissions/",
        views.admin_assignment_submissions,
        name="admin_assignment_submissions",
    ),
    path(
        "students/edit/<int:student_id>/",
        views.edit_student,
        name="edit_student",
    ),
    path(
        "students/delete/<int:student_id>/",
        views.delete_student,
        name="delete_student",
    ),

    # Teachers
    path(
        "admin/admin-teachers/",
        views.admin_teachers,
        name="admin_teachers",
    ),
    path(
        "admin/add-teacher/",
        views.add_teacher,
        name="add_teacher",
    ),
    path(
        "admin/edit-teacher/<int:teacher_id>/",
        views.edit_teacher,
        name="edit_teacher",
    ),
    path(
        "admin/delete-teacher/<int:teacher_id>/",
        views.delete_teacher,
        name="delete_teacher",
    ),
    path(
        "admin/assign-teacher-subject/",
        views.assign_teacher_subject,
        name="assign_teacher_subject",
    ),

    # Subjects
    path(
        "admin/admin-subjects/",
        views.admin_subjects,
        name="admin_subjects",
    ),
    path(
        "admin/add-subject/",
        views.add_subject,
        name="add_subject",
    ),
    path(
        "admin/edit-subject/<int:subject_id>/",
        views.edit_subject,
        name="edit_subject",
    ),
    path(
        "admin/delete-subject/<int:subject_id>/",
        views.delete_subject,
        name="delete_subject",
    ),

    # Courses
    path("admin/admin_courses/", views.admin_courses, name="admin_courses"),
    path("admin/add-course/", views.add_course, name="add_course"),
    path(
        "admin/edit-course/<int:course_id>/edit/",
        views.edit_course,
        name="edit_course",
    ),
    path(
        "admin/delete-course/<int:course_id>/",
        views.delete_course,
        name="delete_course",
    ),

    # Lessons
    path("admin/admin_lessons/", views.admin_lessons, name="admin_lessons"),
    path("admin/add-lesson/", views.add_lesson, name="add_lesson"),
    path(
        "admin/lesson/<int:lesson_id>/edit/",
        views.edit_lesson,
        name="edit_lesson",
    ),
    path(
        "admin/lesson/<int:lesson_id>/delete/",
        views.delete_lesson,
        name="delete_lesson",
    ),

    # Quizzes
    path("admin/admin_quizzes/", views.admin_quizzes, name="admin_quizzes"),
    path("admin/add-quiz/", views.add_quiz, name="add_quiz"),
    path(
        "admin/quiz/<int:quiz_id>/edit/",
        views.edit_quiz,
        name="edit_quiz",
    ),
    path(
        "admin/quiz/<int:quiz_id>/delete/",
        views.delete_quiz,
        name="delete_quiz",
    ),

    # Assignments
    path(
        "admin/admin_assignments/",
        views.admin_assignments,
        name="admin_assignments",
    ),
    path(
        "admin/add-assignment/",
        views.add_assignment,
        name="add_assignment",
    ),
    path(
        "admin/assignment/<int:assignment_id>/edit/",
        views.edit_assignment,
        name="edit_assignment",
    ),
    path(
        "admin/assignment/<int:assignment_id>/delete/",
        views.delete_assignment,
        name="delete_assignment",
    ),

    # Payments
    path(
        "admin/admin_payments/",
        views.admin_payments,
        name="admin_payments",
    ),
    path(
        "admin/payment/<int:payment_id>/accept/",
        views.accept_payment,
        name="accept_payment",
    ),

    # Certificates
    path(
        "admin/admin_certificates/",
        views.admin_certificates,
        name="admin_certificates",
    ),
    path(
        "admin/add-certificate/",
        views.add_certificate,
        name="add_certificate",
    ),
    path(
        "admin/certificate/<int:certificate_id>/delete/",
        views.delete_certificate,
        name="delete_certificate",
    ),
    path(
        "admin/certificate/<int:certificate_id>/edit/",
        views.edit_certificate,
        name="edit_certificate",
    ),
]