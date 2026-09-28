from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from courses.models import (
    Course, CourseDetails, Subject, Lesson, LessonProgress,
    Quiz, Assignment, Payment, Certificate, StudentEnrollment,
    TeacherEnrollment, QuizSubmission, AssignmentSubmission,
)
from accounts.models import User
from django.db.models import Q

# --- Student Views ---
def student_dashboard(request):
    user_id = request.session.get("user_id")
    student = User.objects.filter(id=user_id, role="student").first()
    if not student:
        return redirect("login")

    enrollments = StudentEnrollment.objects.filter(student_id=user_id).select_related("course")
    enrolled_courses = enrollments.count()
    certificates = Certificate.objects.filter(student_id=user_id).count()
    completed_courses = 0

    for enrollment in enrollments:
        course = enrollment.course
        total_lessons = Lesson.objects.filter(subject__courses=course).distinct().count()
        completed_lessons = LessonProgress.objects.filter(
            student_id=user_id, lesson__subject__courses=course, completed=True
        ).distinct().count()

        if total_lessons > 0 and completed_lessons >= total_lessons:
            completed_courses += 1

        enrollment.total_lessons = total_lessons
        enrollment.completed_lessons = completed_lessons
        enrollment.progress = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

    context = {
        "student": student,
        "enrolled_courses": enrolled_courses,
        "completed_courses": completed_courses,
        "certificates": certificates,
        "enrollments": enrollments, }
    return render(request, "dashboard/student/student_dashboard.html", context)

def my_courses(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    enrollments = StudentEnrollment.objects.filter(student_id=user_id).select_related("course")

    for enrollment in enrollments:
        course = enrollment.course
        total_lessons = Lesson.objects.filter(subject__courses=course).distinct().count()
        completed_lessons = LessonProgress.objects.filter(
            student_id=user_id, lesson__subject__courses=course, completed=True
        ).distinct().count()

        enrollment.total_lessons = total_lessons
        enrollment.completed_lessons = completed_lessons
        enrollment.progress = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

    return render(request, "dashboard/student/my_courses.html", {"enrollments": enrollments})

def course_learning(request, course_id):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    course = get_object_or_404(Course, id=course_id, enrollments__student_id=user_id)
    subjects = Subject.objects.filter(courses=course).order_by("id")
    lessons = list(Lesson.objects.filter(subject__in=subjects).order_by("subject_id", "id"))

    completed_lesson_ids = set(
        LessonProgress.objects.filter(
            student_id=user_id, lesson__in=lessons, completed=True
        ).values_list("lesson_id", flat=True)
    )

    first_incomplete_lesson = next(
        (l for l in lessons if l.id not in completed_lesson_ids), None
    )

    lesson_id = request.GET.get("lesson")
    if lesson_id:
        requested_lesson = get_object_or_404(Lesson, id=lesson_id, subject__in=subjects)
    else:
        requested_lesson = first_incomplete_lesson or (lessons[-1] if lessons else None)

    current_lesson = requested_lesson

    if current_lesson:
        current_index = lessons.index(current_lesson)
        can_access = all(l.id in completed_lesson_ids for l in lessons[:current_index])
        if not can_access:
            current_lesson = first_incomplete_lesson

    previous_lesson = None
    next_lesson = None
    is_completed = False

    if current_lesson:
        current_index = lessons.index(current_lesson)
        is_completed = current_lesson.id in completed_lesson_ids
        if current_index > 0:
            previous_lesson = lessons[current_index - 1]
        if current_index < len(lessons) - 1 and is_completed:
            next_lesson = lessons[current_index + 1]

    lesson_data = []
    previous_completed = True

    for lesson in lessons:
        lesson_data.append({
            "lesson": lesson,
            "completed": lesson.id in completed_lesson_ids,
            "locked": not previous_completed,
        })
        if lesson.id not in completed_lesson_ids:
            previous_completed = False

    if request.method == "POST":
        lesson_id = request.POST.get("lesson_id")
        lesson = get_object_or_404(Lesson, id=lesson_id, subject__in=subjects)
        lesson_index = lessons.index(lesson)

        if all(l.id in completed_lesson_ids for l in lessons[:lesson_index]):
            LessonProgress.objects.update_or_create(
                student_id=user_id, lesson=lesson, defaults={"completed": True}
            )
        return redirect("course_learning", course_id=course.id)
    return render(request, "dashboard/student/course_learning.html", {
        "course": course,
        "subjects": subjects,
        "lessons": lessons,
        "lesson_data": lesson_data,
        "current_lesson": current_lesson,
        "previous_lesson": previous_lesson,
        "next_lesson": next_lesson,
        "is_completed": is_completed,
    })

def quiz(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    courses = Course.objects.filter(enrollments__student_id=user_id)
    quizzes = Quiz.objects.filter(
        subject__courses__in=courses
    ).select_related("subject").distinct()

    search = request.GET.get("search", "").strip()
    if search:
        quizzes = quizzes.filter(
            Q(quiz_name__icontains=search) |
            Q(subject__name__icontains=search)
        )

    subject_id = request.GET.get("subject", "")
    if subject_id:
        quizzes = quizzes.filter(subject_id=subject_id)

    subjects = Subject.objects.filter(
        courses__enrollments__student_id=user_id
    ).distinct().order_by("name")

    for quiz_obj in quizzes:
        quiz_obj.latest_submission = QuizSubmission.objects.filter(
            quiz=quiz_obj, student_id=user_id
        ).order_by("-submitted_at").first()

    status = request.GET.get("status", "")
    if status:
        filtered_quizzes = []

        for quiz_obj in quizzes:
            submission = quiz_obj.latest_submission

            if status == "pending" and submission is None:
                filtered_quizzes.append(quiz_obj)
            elif status == "submitted" and submission and submission.score is None:
                filtered_quizzes.append(quiz_obj)
            elif status == "graded" and submission and submission.score is not None:
                filtered_quizzes.append(quiz_obj)

        quizzes = filtered_quizzes
    return render(request, "dashboard/student/quiz.html", {
        "quizzes": quizzes,
        "subjects": subjects,
        "search": search,
        "subject_id": subject_id,
        "status": status,
    })

def quiz_detail(request, quiz_id):
    user_id = request.session.get("user_id")
    quiz_obj = get_object_or_404(
        Quiz, id=quiz_id,
        subject__courses__enrollments__student_id=user_id)

    if request.method == "POST":
        answer_pdf = request.FILES.get("answer_pdf")
        if not answer_pdf:
            messages.error(request, "Please upload your answer PDF.")
            return redirect("quiz_detail", quiz_id=quiz_obj.id)

        QuizSubmission.objects.create(
            quiz=quiz_obj,
            student_id=user_id,
            question_pdf=quiz_obj.question_pdf,
            answer_pdf=answer_pdf
        )
        messages.success(request, "Your quiz answer has been submitted successfully.")
        return redirect("quiz")
    return render(request, "dashboard/student/quiz_detail.html", {"quiz": quiz_obj})

def assignment(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    courses = Course.objects.filter(enrollments__student_id=user_id)
    assignments = Assignment.objects.filter(
        subject__courses__in=courses
    ).select_related("subject").distinct()

    search = request.GET.get("search", "").strip()
    if search:
        assignments = assignments.filter(
            Q(assignment_name__icontains=search) |
            Q(subject__name__icontains=search))

    subject_id = request.GET.get("subject", "")
    if subject_id:
        assignments = assignments.filter(subject_id=subject_id)

    subjects = Subject.objects.filter(
        courses__enrollments__student_id=user_id
    ).distinct().order_by("name")

    for assignment_obj in assignments:
        assignment_obj.latest_submission = AssignmentSubmission.objects.filter(
            assignment=assignment_obj, student_id=user_id
        ).order_by("-submitted_at").first()

    status = request.GET.get("status", "")
    if status:
        filtered_assignments = []

        for assignment_obj in assignments:
            submission = assignment_obj.latest_submission

            if status == "pending" and submission is None:
                filtered_assignments.append(assignment_obj)
            elif status == "submitted" and submission and submission.score is None:
                filtered_assignments.append(assignment_obj)
            elif status == "graded" and submission and submission.score is not None:
                filtered_assignments.append(assignment_obj)

        assignments = filtered_assignments
    return render(request, "dashboard/student/assignment.html", {
        "assignments": assignments,
        "subjects": subjects,
        "search": search,
        "subject_id": subject_id,
        "status": status,
    })

def assignment_detail(request, assignment_id):
    user_id = request.session.get("user_id")
    assignment_obj = get_object_or_404(
        Assignment, id=assignment_id,
        subject__courses__enrollments__student_id=user_id)

    if request.method == "POST":
        answer_pdf = request.FILES.get("answer_pdf")
        if not answer_pdf:
            messages.error(request, "Please upload your answer PDF.")
            return redirect("assignment_detail", assignment_id=assignment_obj.id)

        AssignmentSubmission.objects.create(
            assignment=assignment_obj,
            student_id=user_id,
            question_pdf=assignment_obj.question_pdf,
            answer_pdf=answer_pdf)
        messages.success(request, "Your assignment answer has been submitted successfully.")
        return redirect("assignment")
    return render(
        request,
        "dashboard/student/assignment_detail.html",
        {"assignment": assignment_obj})

def grades(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    search = request.GET.get("search", "").strip()
    course_id = request.GET.get("course", "")

    courses = Course.objects.filter(
        enrollments__student_id=user_id
    ).distinct()

    if course_id:
        courses = courses.filter(id=course_id)

    subjects = Subject.objects.filter(
        courses__in=courses
    ).distinct()

    if search:
        subjects = subjects.filter(name__icontains=search)

    grade_data = []

    for subject in subjects:
        quiz_submission = QuizSubmission.objects.filter(
            student_id=user_id,
            quiz__subject=subject,
            score__isnull=False
        ).order_by("-submitted_at").first()

        assignment_submission = AssignmentSubmission.objects.filter(
            student_id=user_id,
            assignment__subject=subject,
            score__isnull=False
        ).order_by("-submitted_at").first()

        quiz_score = quiz_submission.score if quiz_submission else None
        assignment_score = assignment_submission.score if assignment_submission else None

        scores = []
        if quiz_score is not None:
            scores.append(float(quiz_score))
        if assignment_score is not None:
            scores.append(float(assignment_score))

        overall = sum(scores) / len(scores) if scores else None
        grade = None

        if overall is not None:
            if overall >= 90:
                grade = "A+"
            elif overall >= 80:
                grade = "A"
            elif overall >= 70:
                grade = "B+"
            elif overall >= 60:
                grade = "B"
            elif overall >= 50:
                grade = "C"
            else:
                grade = "F"

        grade_data.append({
            "subject": subject,
            "quiz_score": quiz_score,
            "assignment_score": assignment_score,
            "overall": overall,
            "grade": grade,
        })

    return render(request, "dashboard/student/grades.html", {
        "grade_data": grade_data,
        "courses": Course.objects.filter(
            enrollments__student_id=user_id
        ).distinct(),
        "search": search,
        "course_id": course_id,})

def certificates(request):
    user_id = request.session.get("user_id")
    certificates_qs = Certificate.objects.filter(
        student_id=user_id
    ).select_related("course")

    return render(request, "dashboard/student/certificates.html", {
        "certificates": certificates_qs
    })

def student_profile(request):
    user_id = request.session.get("user_id")
    student = User.objects.filter(id=user_id, role="student").first()

    if not student:
        return redirect("login")

    if request.method == "POST":
        student.name = request.POST.get("name", "").strip()
        student.email = request.POST.get("email", "").strip()
        student.phone = request.POST.get("phone", "").strip()
        student.save()

        messages.success(request, "Your profile has been updated successfully.")
        return redirect("student_dashboard")

    return render(request, "dashboard/student/student_profile.html", {
        "student": student
    })

def teacher_profile(request):
    user_id = request.session.get("user_id")
    teacher = User.objects.filter(id=user_id, role="teacher").first()
    if not teacher:
        return redirect("login")

    if request.method == "POST":
        teacher.name = request.POST.get("name", "").strip()
        teacher.email = request.POST.get("email", "").strip()
        teacher.phone = request.POST.get("phone", "").strip()
        teacher.save()
        messages.success(request, "Your profile has been updated successfully.")
        return redirect("teacher_dashboard")
    return render(request, "dashboard/teacher/teacher_profile.html", {"teacher": teacher})


def teacher_dashboard(request):
    user_id = request.session.get("user_id")
    teacher = User.objects.filter(id=user_id, role="teacher").first()

    if not teacher:
        return redirect("login")

    my_subjects = TeacherEnrollment.objects.filter(teacher=teacher).count()
    quiz_submissions = QuizSubmission.objects.filter(
        quiz__subject__teacher_enrollments__teacher=teacher
    ).distinct().count()
    assignment_submissions = AssignmentSubmission.objects.filter(
        assignment__subject__teacher_enrollments__teacher=teacher
    ).distinct().count()

    context = {
        "teacher": teacher,
        "my_subjects": my_subjects,
        "quiz_submissions": quiz_submissions,
        "assignment_submissions": assignment_submissions,
    }
    return render(request, "dashboard/teacher/teacher_dashboard.html", context)

def teacher_subjects(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    teacher = User.objects.filter(id=user_id, role="teacher").first()
    if not teacher:
        return redirect("login")

    teacher_enrollments = TeacherEnrollment.objects.filter(
        teacher=teacher
    ).select_related("subject")

    subjects = []
    for enrollment in teacher_enrollments:
        subject = enrollment.subject
        subjects.append({
            "subject": subject,
            "lessons": Lesson.objects.filter(subject=subject),
            "quizzes": Quiz.objects.filter(subject=subject),
            "assignments": Assignment.objects.filter(subject=subject),
        })

    return render(request, "dashboard/teacher/teacher_subjects.html", {"subjects": subjects})

def teacher_quiz_submissions(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    teacher = User.objects.filter(id=user_id, role="teacher").first()
    if not teacher:
        return redirect("login")

    submissions = QuizSubmission.objects.filter(
        quiz__subject__teacher_enrollments__teacher=teacher
    ).select_related(
        "student", "quiz", "quiz__subject"
    ).order_by("-submitted_at")

    search = request.GET.get("search", "").strip()
    if search:
        submissions = submissions.filter(
            Q(student__name__icontains=search) |
            Q(quiz__quiz_name__icontains=search) |
            Q(quiz__subject__name__icontains=search)
        )

    subject_id = request.GET.get("subject", "")
    if subject_id:
        submissions = submissions.filter(quiz__subject_id=subject_id)

    status = request.GET.get("status", "")
    if status == "pending":
        submissions = submissions.filter(score__isnull=True)
    elif status == "graded":
        submissions = submissions.filter(score__isnull=False)

    subjects = Subject.objects.filter(
        teacher_enrollments__teacher=teacher
    ).distinct().order_by("name")
    return render(request, "dashboard/teacher/teacher_quiz_submissions.html", {
        "submissions": submissions,
        "subjects": subjects,
        "search": search,
        "subject_id": subject_id,
        "status": status,
    })

def teacher_quiz_submission_detail(request, submission_id):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    teacher = User.objects.filter(id=user_id, role="teacher").first()
    if not teacher:
        return redirect("login")

    submission = get_object_or_404(
        QuizSubmission.objects.select_related(
            "student", "quiz", "quiz__subject"
        ).filter(
            quiz__subject__teacher_enrollments__teacher=teacher
        ),
        id=submission_id
    )

    if request.method == "POST":
        score = request.POST.get("score")
        if score:
            submission.score = score
            submission.graded_by = teacher
            submission.save()
            messages.success(request, "Quiz grade saved successfully.")
            return redirect("teacher_quiz_submissions")
    return render(
        request,
        "dashboard/teacher/teacher_quiz_submission_detail.html",
        {"submission": submission}
    )

def teacher_assignment_submissions(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    teacher = User.objects.filter(id=user_id, role="teacher").first()
    if not teacher:
        return redirect("login")

    submissions = AssignmentSubmission.objects.filter(
        assignment__subject__teacher_enrollments__teacher=teacher
    ).select_related(
        "student", "assignment", "assignment__subject"
    ).order_by("-submitted_at")

    search = request.GET.get("search", "").strip()
    if search:
        submissions = submissions.filter(
            Q(student__name__icontains=search) |
            Q(assignment__assignment_name__icontains=search) |
            Q(assignment__subject__name__icontains=search)
        )

    subject_id = request.GET.get("subject", "")
    if subject_id:
        submissions = submissions.filter(assignment__subject_id=subject_id)

    status = request.GET.get("status", "")
    if status == "pending":
        submissions = submissions.filter(score__isnull=True)
    elif status == "graded":
        submissions = submissions.filter(score__isnull=False)

    subjects = Subject.objects.filter(
        teacher_enrollments__teacher=teacher
    ).distinct().order_by("name")

    return render(request, "dashboard/teacher/teacher_assignment_submissions.html", {
        "submissions": submissions,
        "subjects": subjects,
        "search": search,
        "subject_id": subject_id,
        "status": status,
    })

def teacher_assignment_submission_detail(request, submission_id):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    teacher = User.objects.filter(id=user_id, role="teacher").first()
    if not teacher:
        return redirect("login")

    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related(
            "student", "assignment", "assignment__subject"
        ).filter(
            assignment__subject__teacher_enrollments__teacher=teacher
        ),id=submission_id)

    if request.method == "POST":
        score = request.POST.get("score")
        if score:
            submission.score = score
            submission.graded_by = teacher
            submission.save()
            messages.success(request, "Assignment grade saved successfully.")
            return redirect("teacher_assignment_submissions")
    return render(
        request,
        "dashboard/teacher/teacher_assignment_submission_detail.html",
        {"submission": submission})

def teacher_grades(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    teacher = User.objects.filter(id=user_id, role="teacher").first()
    if not teacher:
        return redirect("login")

    teacher_subjects = Subject.objects.filter(
        teacher_enrollments__teacher=teacher
    ).distinct()

    search = request.GET.get("search", "").strip()
    subject_id = request.GET.get("subject", "")
    subjects = teacher_subjects.order_by("name")

    quiz_submissions = QuizSubmission.objects.filter(
        quiz__subject__in=teacher_subjects,
        score__isnull=False
    ).select_related("student", "quiz", "quiz__subject")

    assignment_submissions = AssignmentSubmission.objects.filter(
        assignment__subject__in=teacher_subjects,
        score__isnull=False
    ).select_related("student", "assignment", "assignment__subject")

    if subject_id:
        quiz_submissions = quiz_submissions.filter(quiz__subject_id=subject_id)
        assignment_submissions = assignment_submissions.filter(
            assignment__subject_id=subject_id)

    grade_data = {}

    for submission in quiz_submissions:
        key = (submission.student.id, submission.quiz.subject.id)

        if key not in grade_data:
            grade_data[key] = {
                "student": submission.student,
                "subject": submission.quiz.subject,
                "quiz_scores": [],
                "assignment_scores": []}

        grade_data[key]["quiz_scores"].append(float(submission.score))

    for submission in assignment_submissions:
        key = (submission.student.id, submission.assignment.subject.id)

        if key not in grade_data:
            grade_data[key] = {
                "student": submission.student,
                "subject": submission.assignment.subject,
                "quiz_scores": [],
                "assignment_scores": []}

        grade_data[key]["assignment_scores"].append(float(submission.score))

    grades_list = []

    for item in grade_data.values():
        if search:
            search_lower = search.lower()
            if (
                search_lower not in item["student"].name.lower()
                and search_lower not in item["subject"].name.lower()
            ):
                continue

        quiz_scores = item["quiz_scores"]
        assignment_scores = item["assignment_scores"]

        quiz_score = sum(quiz_scores) / len(quiz_scores) if quiz_scores else None
        assignment_score = (
            sum(assignment_scores) / len(assignment_scores)
            if assignment_scores else None
        )

        scores = []
        if quiz_score is not None:
            scores.append(quiz_score)
        if assignment_score is not None:
            scores.append(assignment_score)

        overall = sum(scores) / len(scores) if scores else None
        grade = ""

        if overall is not None:
            if overall >= 90:
                grade = "A+"
            elif overall >= 80:
                grade = "A"
            elif overall >= 70:
                grade = "B+"
            elif overall >= 60:
                grade = "B"
            elif overall >= 50:
                grade = "C"
            else:
                grade = "F"

        grades_list.append({
            "student": item["student"],
            "subject": item["subject"],
            "quiz_score": quiz_score,
            "assignment_score": assignment_score,
            "overall": overall,
            "grade": grade,
        })

    grades_list.sort(key=lambda item: (
        item["student"].name.lower(),
        item["subject"].name.lower()
    ))

    return render(request, "dashboard/teacher/teacher_grades.html", {
        "grades": grades_list,
        "subjects": subjects,
        "search": search,
        "subject_id": subject_id,
    })

# --- Admin Views ---
def admin_dashboard(request):
    user_id = request.session.get("user_id")
    admin = User.objects.filter(id=user_id, role="admin").first()

    if not admin:
        return redirect("login")
    context = {
        "total_students": User.objects.filter(role="student").count(),
        "total_teachers": User.objects.filter(role="teacher").count(),
        "total_courses": Course.objects.count(),
        "total_subjects": Subject.objects.count(),
    }
    return render(request, "dashboard/admin/admin_dashboard.html", context)

def admin_students(request):
    user_id = request.session.get("user_id")
    admin = User.objects.filter(id=user_id, role="admin").first()

    if not admin:
        return redirect("login")

    students = User.objects.filter(role="student").order_by("-id")
    search = request.GET.get("search", "")
    selected_course = request.GET.get("course", "")

    if search:
        students = students.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )

    if selected_course:
        students = students.filter(
            enrollments__course_id=selected_course
        ).distinct()

    courses = Course.objects.all().order_by("name")

    for student in students:
        student.course_progress = []
        enrollments = StudentEnrollment.objects.filter(
            student=student
        ).select_related("course")

        for enrollment in enrollments:
            course = enrollment.course

            total_lessons = Lesson.objects.filter(
                subject__courses=course
            ).distinct().count()

            completed_lessons = LessonProgress.objects.filter(
                student=student,
                lesson__subject__courses=course,
                completed=True
            ).distinct().count()

            quizzes = Quiz.objects.filter(
                subject__courses=course
            ).distinct()

            total_quizzes = quizzes.count()
            passed_quizzes = 0

            for quiz in quizzes:
                submission = QuizSubmission.objects.filter(
                    student=student,
                    quiz=quiz,
                    score__isnull=False
                ).order_by("-submitted_at").first()

                if submission and submission.score >= quiz.passing_score:
                    passed_quizzes += 1

            assignments = Assignment.objects.filter(
                subject__courses=course
            ).distinct()

            total_assignments = assignments.count()
            passed_assignments = 0

            for assignment in assignments:
                submission = AssignmentSubmission.objects.filter(
                    student=student,
                    assignment=assignment,
                    score__isnull=False
                ).order_by("-submitted_at").first()

                if submission and submission.score >= assignment.passing_score:
                    passed_assignments += 1

            lessons_complete = (
                total_lessons == 0 or completed_lessons >= total_lessons
            )
            quizzes_complete = (
                total_quizzes == 0 or passed_quizzes >= total_quizzes
            )
            assignments_complete = (
                total_assignments == 0 or
                passed_assignments >= total_assignments
            )

            student.course_progress.append({
                "course": course,
                "completed": (
                    lessons_complete and
                    quizzes_complete and
                    assignments_complete
                ),
                "completed_lessons": completed_lessons,
                "total_lessons": total_lessons,
                "passed_quizzes": passed_quizzes,
                "total_quizzes": total_quizzes,
                "passed_assignments": passed_assignments,
                "total_assignments": total_assignments,
            })
    return render(request, "dashboard/admin/admin_students.html", {
        "students": students,
        "courses": courses,
        "search": search,
        "selected_course": selected_course})

def edit_student(request, student_id):
    student = User.objects.get(id=student_id, role="student")

    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")

        if User.objects.filter(email=email).exclude(id=student_id).exists():
            messages.error(request, "Email already exists.")
            return redirect("edit_student", student_id=student_id)

        student.name = name
        student.email = email
        student.phone = phone

        if password:
            student.password = make_password(password)

        student.save()
        messages.success(request, "Student updated successfully.")
        return redirect("admin_students")

    return render(
        request,
        "dashboard/admin/edit_student.html",
        {"student": student})

def delete_student(request, student_id):
    student = User.objects.get(id=student_id, role="student")
    student.delete()
    messages.success(request, "Student deleted successfully.")
    return redirect("admin_students")

def admin_student_grades(request):
    user_id = request.session.get("user_id")
    admin = User.objects.filter(id=user_id, role="admin").first()

    if not admin:
        return redirect("login")

    students = User.objects.filter(role="student").order_by("name")
    search = request.GET.get("search", "").strip()

    if search:
        students = students.filter(name__icontains=search)

    course_id = request.GET.get("course", "")

    if course_id:
        students = students.filter(
            enrollments__course_id=course_id
        ).distinct()

    courses = Course.objects.all().order_by("name")
    grades = []

    for student in students:
        subjects = Subject.objects.filter(
            courses__enrollments__student=student
        ).distinct()

        for subject in subjects:
            quiz_scores = list(
                QuizSubmission.objects.filter(
                    student=student,
                    quiz__subject=subject,
                    score__isnull=False
                ).values_list("score", flat=True)
            )

            assignment_scores = list(
                AssignmentSubmission.objects.filter(
                    student=student,
                    assignment__subject=subject,
                    score__isnull=False
                ).values_list("score", flat=True)
            )

            all_scores = quiz_scores + assignment_scores
            if not all_scores:
                continue

            average = round(sum(all_scores) / len(all_scores), 1)

            if average >= 90:
                grade = "A+"
            elif average >= 80:
                grade = "A"
            elif average >= 75:
                grade = "B+"
            elif average >= 70:
                grade = "B"
            elif average >= 60:
                grade = "C"
            else:
                grade = "F"

            grades.append({
                "student": student,
                "subject": subject,
                "quiz_average": (
                    round(sum(quiz_scores) / len(quiz_scores), 1)
                    if quiz_scores else None
                ),
                "assignment_average": (
                    round(sum(assignment_scores) / len(assignment_scores), 1)
                    if assignment_scores else None
                ),
                "average": average,
                "grade": grade,
            })

    return render(request, "dashboard/admin/admin_student_grades.html", {
        "grades": grades,
        "courses": courses,
        "search": search,
        "course": course_id})

def admin_quiz_submissions(request):
    user_id = request.session.get("user_id")
    admin = User.objects.filter(id=user_id, role="admin").first()

    if not admin:
        return redirect("login")

    submissions = QuizSubmission.objects.select_related(
        "student", "quiz", "quiz__subject", "graded_by"
    ).order_by("-submitted_at")

    search = request.GET.get("search", "").strip()
    if search:
        submissions = submissions.filter(
            Q(student__name__icontains=search) |
            Q(quiz__quiz_name__icontains=search) |
            Q(quiz__subject__name__icontains=search)
        )

    subject_id = request.GET.get("subject", "")
    if subject_id:
        submissions = submissions.filter(quiz__subject_id=subject_id)

    status = request.GET.get("status", "")
    if status == "pending":
        submissions = submissions.filter(score__isnull=True)
    elif status == "graded":
        submissions = submissions.filter(score__isnull=False)

    subjects = Subject.objects.all().order_by("name")

    return render(request, "dashboard/admin/admin_quiz_submissions.html", {
        "submissions": submissions,
        "subjects": subjects,
        "search": search,
        "subject_id": subject_id,
        "status": status})

def admin_assignment_submissions(request):
    user_id = request.session.get("user_id")
    admin = User.objects.filter(id=user_id, role="admin").first()

    if not admin:
        return redirect("login")

    submissions = AssignmentSubmission.objects.select_related(
        "student", "assignment", "assignment__subject", "graded_by"
    ).order_by("-submitted_at")

    search = request.GET.get("search", "").strip()
    if search:
        submissions = submissions.filter(
            Q(student__name__icontains=search) |
            Q(assignment__assignment_name__icontains=search) |
            Q(assignment__subject__name__icontains=search)
        )

    subject_id = request.GET.get("subject", "")
    if subject_id:
        submissions = submissions.filter(
            assignment__subject_id=subject_id
        )

    status = request.GET.get("status", "")
    if status == "pending":
        submissions = submissions.filter(score__isnull=True)
    elif status == "graded":
        submissions = submissions.filter(score__isnull=False)

    subjects = Subject.objects.all().order_by("name")
    return render(request, "dashboard/admin/admin_assignment_submissions.html", {
        "submissions": submissions,
        "subjects": subjects,
        "search": search,
        "subject_id": subject_id,
        "status": status})

def admin_teachers(request):
    teachers = User.objects.filter(role="teacher").order_by("-id")
    search = request.GET.get("search", "").strip()

    if search:
        teachers = teachers.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search))

    subjects = Subject.objects.all().order_by("name")
    teacher_enrollments = TeacherEnrollment.objects.select_related(
        "teacher", "subject")
    return render(request, "dashboard/admin/admin_teachers.html", {
        "teachers": teachers,
        "subjects": subjects,
        "teacher_enrollments": teacher_enrollments,
        "search": search})

def assign_teacher_subject(request):
    if request.method == "POST":
        teacher_id = request.POST.get("teacher")
        subject_id = request.POST.get("subject")

        teacher = User.objects.get(id=teacher_id, role="teacher")
        subject = Subject.objects.get(id=subject_id)

        TeacherEnrollment.objects.get_or_create(
            teacher=teacher,
            subject=subject)
        messages.success(
            request,
            "Subject assigned to teacher successfully.")
    return redirect("admin_teachers")

def add_teacher(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("add_teacher")

        User.objects.create(
            name=name,
            email=email,
            password=make_password(password),
            phone=phone,
            role="teacher")
        messages.success(request, "Teacher account created successfully.")
        return redirect("admin_teachers")
    return render(request, "dashboard/admin/add_teacher.html")

def edit_teacher(request, teacher_id):
    teacher = User.objects.get(id=teacher_id, role="teacher")
    subjects = Subject.objects.all().order_by("name")

    assigned_subject_ids = list(
        TeacherEnrollment.objects.filter(teacher=teacher)
        .values_list("subject_id", flat=True))

    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")

        if User.objects.filter(email=email).exclude(id=teacher_id).exists():
            messages.error(request, "Email already exists.")
            return redirect("edit_teacher", teacher_id=teacher_id)

        teacher.name = name
        teacher.email = email
        teacher.phone = phone

        if password:
            teacher.password = make_password(password)
        teacher.save()

        selected_subjects = request.POST.getlist("subjects")

        TeacherEnrollment.objects.filter(teacher=teacher).exclude(
            subject_id__in=selected_subjects
        ).delete()

        for subject_id in selected_subjects:
            TeacherEnrollment.objects.get_or_create(
                teacher=teacher,
                subject_id=subject_id)

        messages.success(request, "Teacher updated successfully.")
        return redirect("admin_teachers")
    return render(request,"dashboard/admin/edit_teacher.html",
        {
            "teacher": teacher,
            "subjects": subjects,
            "assigned_subject_ids": assigned_subject_ids,
        })

def delete_teacher(request, teacher_id):
    teacher = User.objects.get(id=teacher_id, role="teacher")
    teacher.delete()
    messages.success(request, "Teacher deleted successfully.")
    return redirect("admin_teachers")


def admin_subjects(request):
    subjects = Subject.objects.all()
    search = request.GET.get("search", "").strip()
    sort = request.GET.get("sort", "")

    if search:
        subjects = subjects.filter(name__icontains=search)

    subjects = subjects.order_by("-created_at" if sort == "latest" else "-id")
    return render(request, "dashboard/admin/admin_subjects.html", {
        "subjects": subjects,
        "search": search,
        "sort": sort})

def add_subject(request):
    if request.method == "POST":
        Subject.objects.create(
            name=request.POST.get("name"),
            description=request.POST.get("description"))
        return redirect("admin_subjects")
    return render(request, "dashboard/admin/add_subject.html")

def edit_subject(request, subject_id):
    subject = Subject.objects.get(id=subject_id)

    if request.method == "POST":
        subject.name = request.POST.get("name")
        subject.description = request.POST.get("description")
        subject.save()
        return redirect("admin_subjects")
    return render(
        request,
        "dashboard/admin/edit_subject.html",
        {"subject": subject})

def delete_subject(request, subject_id):
    subject = Subject.objects.get(id=subject_id)
    subject.delete()
    return redirect("admin_subjects")

def admin_courses(request):
    courses = Course.objects.all().order_by("-id")
    search = request.GET.get("search", "").strip()

    if search:
        courses = courses.filter(name__icontains=search)
    return render(request, "dashboard/admin/admin_courses.html", {
        "courses": courses,
        "search": search})

def add_course(request):
    subjects = Subject.objects.all().order_by("name")

    if request.method == "POST":
        course = Course.objects.create(
            name=request.POST.get("name"),
            description=request.POST.get("description"),
            price=request.POST.get("price"),
            image=request.FILES.get("image"))

        for subject_id in request.POST.getlist("subjects"):
            CourseDetails.objects.create(
                course=course,
                subject_id=subject_id)
        return redirect("admin_courses")
    return render(request, "dashboard/admin/add_course.html", {
        "subjects": subjects })

def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    subjects = Subject.objects.all().order_by("name")

    if request.method == "POST":
        course.name = request.POST.get("name")
        course.description = request.POST.get("description")
        course.price = request.POST.get("price")

        if request.FILES.get("image"):
            course.image = request.FILES.get("image")
        course.save()
        CourseDetails.objects.filter(course=course).delete()

        for subject_id in request.POST.getlist("subjects"):
            CourseDetails.objects.create(
                course=course,
                subject_id=subject_id)
        messages.success(request, "Course updated successfully.")
        return redirect("admin_courses")

    selected_subjects = list(
        course.subjects.values_list("id", flat=True))
    return render(request, "dashboard/admin/edit_course.html", {
        "course": course,
        "subjects": subjects,
        "selected_subjects": selected_subjects})

def delete_course(request, course_id):
    course = Course.objects.get(id=course_id)
    course.delete()
    return redirect("admin_courses")

def admin_lessons(request):
    lessons = Lesson.objects.all().order_by("-id")
    search = request.GET.get("search", "").strip()
    subject = request.GET.get("subject", "")

    if search:
        lessons = (
            lessons.filter(lesson_name__icontains=search) |
            lessons.filter(subject__name__icontains=search))

    if subject:
        lessons = lessons.filter(subject_id=subject)

    subjects = Subject.objects.all().order_by("name")

    return render(request, "dashboard/admin/admin_lessons.html", {
        "lessons": lessons,
        "subjects": subjects,
        "search": search,
        "subject": subject})

def add_lesson(request):
    subjects = Subject.objects.all().order_by("name")

    if request.method == "POST":
        subject = Subject.objects.get(id=request.POST.get("subject"))

        Lesson.objects.create(
            subject=subject,
            lesson_name=request.POST.get("lesson_name"),
            description=request.POST.get("description"),
            link=request.POST.get("link")
        )
        return redirect("admin_lessons")
    return render(request, "dashboard/admin/add_lesson.html", {
        "subjects": subjects })

def edit_lesson(request, lesson_id):
    lesson = Lesson.objects.get(id=lesson_id)
    subjects = Subject.objects.all().order_by("name")

    if request.method == "POST":
        lesson.subject = Subject.objects.get(id=request.POST.get("subject"))
        lesson.lesson_name = request.POST.get("lesson_name")
        lesson.description = request.POST.get("description")
        lesson.link = request.POST.get("link")
        lesson.save()
        return redirect("admin_lessons")

    return render(request, "dashboard/admin/edit_lesson.html", {
        "lesson": lesson,
        "subjects": subjects })

def delete_lesson(request, lesson_id):
    lesson = Lesson.objects.get(id=lesson_id)
    lesson.delete()
    return redirect("admin_lessons")

def admin_quizzes(request):
    quizzes = Quiz.objects.all().order_by("-id")
    search = request.GET.get("search", "").strip()
    subject = request.GET.get("subject", "")

    if search:
        quizzes = (
            quizzes.filter(quiz_name__icontains=search) |
            quizzes.filter(subject__name__icontains=search))
    if subject:
        quizzes = quizzes.filter(subject_id=subject)

    subjects = Subject.objects.all().order_by("name")
    return render(request, "dashboard/admin/admin_quizzes.html", {
        "quizzes": quizzes,
        "subjects": subjects,
        "search": search,
        "subject": subject })

def add_quiz(request):
    subjects = Subject.objects.all().order_by("name")

    if request.method == "POST":
        subject = Subject.objects.get(id=request.POST.get("subject"))

        Quiz.objects.create(
            subject=subject,
            quiz_name=request.POST.get("quiz_name"),
            description=request.POST.get("description"),
            passing_score=request.POST.get("passing_score"),
            question_pdf=request.FILES.get("question_pdf")
        )
        return redirect("admin_quizzes")
    return render(request, "dashboard/admin/add_quiz.html", {
        "subjects": subjects })

def edit_quiz(request, quiz_id):
    quiz_obj = Quiz.objects.get(id=quiz_id)
    subjects = Subject.objects.all().order_by("name")

    if request.method == "POST":
        quiz_obj.subject = Subject.objects.get(id=request.POST.get("subject"))
        quiz_obj.quiz_name = request.POST.get("quiz_name")
        quiz_obj.description = request.POST.get("description")
        quiz_obj.passing_score = request.POST.get("passing_score")

        if request.FILES.get("question_pdf"):
            quiz_obj.question_pdf = request.FILES.get("question_pdf")

        quiz_obj.save()
        return redirect("admin_quizzes")

    return render(request, "dashboard/admin/edit_quiz.html", {
        "quiz": quiz_obj,
        "subjects": subjects })


def delete_quiz(request, quiz_id):
    quiz_obj = Quiz.objects.get(id=quiz_id)
    quiz_obj.delete()
    return redirect("admin_quizzes")

def admin_assignments(request):
    assignments = Assignment.objects.all().order_by("-id")
    search = request.GET.get("search", "").strip()
    subject = request.GET.get("subject", "")

    if search:
        assignments = (
            assignments.filter(assignment_name__icontains=search) |
            assignments.filter(subject__name__icontains=search))

    if subject:
        assignments = assignments.filter(subject_id=subject)

    subjects = Subject.objects.all().order_by("name")
    return render(request, "dashboard/admin/admin_assignments.html", {
        "assignments": assignments,
        "subjects": subjects,
        "search": search,
        "subject": subject })

def add_assignment(request):
    subjects = Subject.objects.all().order_by("name")

    if request.method == "POST":
        subject = Subject.objects.get(id=request.POST.get("subject"))

        Assignment.objects.create(
            subject=subject,
            assignment_name=request.POST.get("assignment_name"),
            description=request.POST.get("description"),
            passing_score=request.POST.get("passing_score"),
            question_pdf=request.FILES.get("question_pdf"))
        return redirect("admin_assignments")
    return render(request, "dashboard/admin/add_assignment.html", {
        "subjects": subjects })

def edit_assignment(request, assignment_id):
    assignment_obj = Assignment.objects.get(id=assignment_id)
    subjects = Subject.objects.all().order_by("name")

    if request.method == "POST":
        assignment_obj.subject = Subject.objects.get(
            id=request.POST.get("subject"))

        assignment_obj.assignment_name = request.POST.get("assignment_name")
        assignment_obj.description = request.POST.get("description")
        assignment_obj.passing_score = request.POST.get("passing_score")

        if request.FILES.get("question_pdf"):
            assignment_obj.question_pdf = request.FILES.get("question_pdf")

        assignment_obj.save()
        return redirect("admin_assignments")

    return render(request, "dashboard/admin/edit_assignment.html", {
        "assignment": assignment_obj,
        "subjects": subjects })

def delete_assignment(request, assignment_id):
    assignment_obj = Assignment.objects.get(id=assignment_id)
    assignment_obj.delete()
    return redirect("admin_assignments")

def admin_payments(request):
    payments = Payment.objects.all().order_by("-id")
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "")

    if search:
        payments = (
            payments.filter(student__name__icontains=search) |
            payments.filter(course__name__icontains=search) |
            payments.filter(transaction_id__icontains=search) )

    if status in ["pending", "accepted"]:
        payments = payments.filter(status=status)

    return render(request, "dashboard/admin/admin_payments.html", {
        "payments": payments,
        "search": search,
        "status": status })

def accept_payment(request, payment_id):
    payment = Payment.objects.get(id=payment_id)
    payment.status = "accepted"
    payment.save()

    StudentEnrollment.objects.get_or_create(
        student=payment.student,
        course=payment.course )
    return redirect("admin_payments")

def admin_certificates(request):
    certificates = Certificate.objects.all().order_by("-id")
    search = request.GET.get("search", "").strip()
    course = request.GET.get("course", "")

    if search:
        certificates = (
            certificates.filter(student__name__icontains=search) |
            certificates.filter(course__name__icontains=search) )

    if course:
        certificates = certificates.filter(course_id=course)

    courses = Course.objects.all().order_by("name")

    return render(request, "dashboard/admin/admin_certificates.html", {
        "certificates": certificates,
        "courses": courses,
        "search": search,
        "course": course })

def add_certificate(request):
    students = User.objects.filter(role="student").order_by("name")
    courses = Course.objects.all().order_by("name")

    if request.method == "POST":
        student = User.objects.get(id=request.POST.get("student"))
        course = Course.objects.get(id=request.POST.get("course"))

        Certificate.objects.create(
            student=student,
            course=course,
            issued_date=request.POST.get("issued_date"),
            certificate_file=request.FILES.get("certificate_file") )
        return redirect("admin_certificates")
    return render(request, "dashboard/admin/add_certificate.html", {
        "students": students,
        "courses": courses })

def edit_certificate(request, certificate_id):
    certificate_obj = Certificate.objects.get(id=certificate_id)
    students = User.objects.filter(role="student").order_by("name")
    courses = Course.objects.all().order_by("name")

    if request.method == "POST":
        certificate_obj.student = User.objects.get(
            id=request.POST.get("student"))
        certificate_obj.course = Course.objects.get(
            id=request.POST.get("course"))
        certificate_obj.issued_date = request.POST.get("issued_date")

        if request.FILES.get("certificate_file"):
            certificate_obj.certificate_file = request.FILES.get(
                "certificate_file")
        certificate_obj.save()
        return redirect("admin_certificates")
    return render(request, "dashboard/admin/edit_certificate.html", {
        "certificate": certificate_obj,
        "students": students,
        "courses": courses })

def delete_certificate(request, certificate_id):
    certificate_obj = get_object_or_404(Certificate, id=certificate_id)
    certificate_obj.delete()
    return redirect("admin_certificates")

def profile(request):
    user_id = request.session.get("user_id")
    admin = User.objects.filter(id=user_id, role="admin").first()

    if not admin:
        return redirect("login")

    if request.method == "POST":
        admin.name = request.POST.get("name", "").strip()
        admin.email = request.POST.get("email", "").strip()
        admin.phone = request.POST.get("phone", "").strip()
        admin.save()

        messages.success(request, "Your profile has been updated successfully.")
        return redirect("profile")
    return render(request, "dashboard/admin/profile.html", {"admin": admin})