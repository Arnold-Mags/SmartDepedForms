from django.views.generic import TemplateView, ListView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.db.models import Count, Avg, Q
from django.http import JsonResponse
from .models import (
    Student,
    AcademicRecord,
    SubjectGrade,
    LearningArea,
    AcademicYear,
    Section,
    TeacherProfile,
)


class DashboardRedirectView(LoginRequiredMixin, RedirectView):
    """
    Redirects users to their appropriate dashboard based on their group
    """

    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.is_superuser:
            return "/admin/"  # Admin goes to Django Admin
        elif user.groups.filter(name="Teacher").exists():
            return "/dashboard/teacher/"
        elif user.groups.filter(name="Registrar").exists():
            return "/dashboard/teacher/"  # Registrar uses same dashboard for student management
        elif user.groups.filter(name="Principal").exists():
            return "/dashboard/principal/"
        else:
            return "/admin/"  # Default fallback


class TeacherDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Student
    template_name = "dashboard_teacher.html"
    context_object_name = "students"
    paginate_by = 20

    def test_func(self):
        user = self.request.user
        return (
            user.groups.filter(name__in=["Teacher", "Registrar"]).exists()
            or user.is_superuser
        )

    def get_queryset(self):
        user = self.request.user
        qs = Student.objects.all()

        # Get selected school year from request or default to current
        selected_year = self.request.GET.get("school_year")

        # If no specific year selected, default to current
        if not selected_year:
            current_year = AcademicYear.get_current_year()
            selected_year = current_year.year_label if current_year else None

        # Apply Academic Year Filter Globally if a year is selected/active
        if selected_year:
            qs = qs.filter(academic_records__school_year=selected_year).distinct()

        # Registrar and Superuser see all students (filtered by year)
        if user.is_superuser or user.groups.filter(name="Registrar").exists():
            return qs.order_by("last_name", "first_name")

        # Teachers only see students in their advisory
        try:
            profile = user.teacher_profile

            # Base filter for teacher's section
            students_in_section = qs.filter(
                academic_records__grade_level=profile.grade_level,
                academic_records__section=profile.section,
            )

            # Note: The 'qs' is already filtered by academic year above if selected_year is present.
            # So students_in_section is effectively:
            # Students with a record in (Year X) AND (Grade/Section Y)

            # Promotion Logic:
            # If viewing CURRENT year, hide students who have been promoted OUT.
            # If viewing PAST year, show all students who were in that section that year.

            current_year_obj = AcademicYear.get_current_year()
            is_viewing_current = not selected_year or (
                current_year_obj and selected_year == current_year_obj.year_label
            )

            if is_viewing_current:
                promoted_students = Student.objects.filter(
                    academic_records__grade_level=profile.grade_level,
                    academic_records__section=profile.section,
                    academic_records__remarks="PROMOTED",
                ).filter(academic_records__grade_level__gt=profile.grade_level)

                students_in_section = students_in_section.exclude(
                    pk__in=promoted_students.values_list("pk", flat=True)
                )

            return students_in_section.distinct().order_by("last_name", "first_name")
        except Exception:
            # If no profile, they see no students (or maybe we show an error)
            return Student.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all students for the table
        students = self.get_queryset()
        context["students"] = students

        # Add academic years to context
        context["academic_years"] = AcademicYear.objects.all().order_by("-start_date")

        # Add selected year
        current_year = AcademicYear.get_current_year()
        selected_year = self.request.GET.get("school_year")
        if not selected_year and current_year:
            selected_year = current_year.year_label
        context["selected_year"] = selected_year

        # Calculate counts for each status
        current_year = AcademicYear.get_current_year()
        is_current_view = not selected_year or (
            current_year and selected_year == current_year.year_label
        )

        if is_current_view:
            # Active count: Only currently enrolled students
            enrolled_count = students.filter(status="ENROLLED").count()
        else:
            # Historical count:
            # User feedback implies they want "Enrolled" to EXCLUDE Transferred/Dropped even historically.
            # Interpreting "Total Enrolled" as "Students from this year who are still Active/Enrolled in the system".
            # Logic: status="ENROLLED"
            enrolled_count = students.filter(status="ENROLLED").count()

        # For Transferred/Dropped, we rely on the STUDENT'S status.
        # Note: This reflects their CURRENT status. If they dropped 2 years ago, they are still "Dropped" now.
        # So filtering the students enrolled in that year by their *current* status is the best approximation.
        transferred_count = students.filter(status="TRANSFERRED").count()
        dropped_count = students.filter(status="DROPPED").count()

        context.update(
            {
                "enrolled_count": enrolled_count,
                "transferred_count": transferred_count,
                "dropped_count": dropped_count,
            }
        )

        # For Registrars: Add Pending Enrollments (Promoted but no section)
        user = self.request.user
        if user.is_superuser or user.groups.filter(name="Registrar").exists():
            pending_records = AcademicRecord.objects.filter(
                school_year=selected_year, section__isnull=True
            ).select_related("student")
            context["pending_records"] = pending_records

        return context


class PrincipalDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "dashboard_principal.html"

    def test_func(self):
        return (
            self.request.user.groups.filter(name="Principal").exists()
            or self.request.user.is_superuser
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filter by Academic Year
        selected_year = self.request.GET.get("school_year")

        # If no specific year selected, default to current
        if not selected_year:
            current_year = AcademicYear.get_current_year()
            selected_year = current_year.year_label if current_year else None

        students_qs = Student.objects.all()
        if selected_year:
            students_qs = students_qs.filter(
                academic_records__school_year=selected_year
            ).distinct()

        # Summary Statistics
        # Total students in this year
        total_students = students_qs.count()

        # Determine if we are viewing the current year
        current_year = AcademicYear.get_current_year()
        is_current_view = not selected_year or (
            current_year and selected_year == current_year.year_label
        )

        if is_current_view:
            # For current year, count only those with explicit ENROLLED status
            enrolled_count = students_qs.filter(status="ENROLLED").count()
        else:
            # For past years, also keep strictly ENROLLED (Active) students to match user expectations
            # "Total Students" (Yellow Card) will still show the full count of records.
            enrolled_count = students_qs.filter(status="ENROLLED").count()

        # Helper subsets
        transferred_count = students_qs.filter(status="TRANSFERRED").count()
        dropped_count = students_qs.filter(status="DROPPED").count()

        # Performance Stats (Sample logic - can be refined)
        # Count passed vs failed/retained in latest records
        latest_records = AcademicRecord.objects.filter(school_year=selected_year)

        passed_count = latest_records.filter(remarks="PASSED").count()
        promoted_count = latest_records.filter(remarks="PROMOTED").count()
        failed_count = latest_records.filter(remarks="FAILED").count()
        retained_count = latest_records.filter(remarks="RETAINED").count()

        # Promoted Students Stats (grouped by Grade and Section)
        # We want to see how many students were promoted FROM each section in the selected year
        promoted_stats = (
            AcademicRecord.objects.filter(school_year=selected_year, remarks="PROMOTED")
            .values("grade_level", "section__name")
            .annotate(count=Count("id"))
            .order_by("grade_level", "section__name")
        )

        context.update(
            {
                "total_students": total_students,
                "enrolled_count": enrolled_count,
                "transferred_count": transferred_count,
                "dropped_count": dropped_count,
                "passed_count": passed_count + promoted_count,
                "failed_count": failed_count + retained_count,
                # Chart Data: Enrollment by Grade (Current/Selected SY)
                "enrollment_by_grade": list(
                    AcademicRecord.objects.filter(
                        school_year=selected_year  # Use the dynamic selected year
                    )
                    .values("grade_level")
                    .annotate(count=Count("id"))
                    .order_by("grade_level")
                ),
                # Chart Data: Performance
                "chart_performance_data": [
                    passed_count + promoted_count,
                    failed_count + retained_count,
                    0,  # Placeholder for Remedial
                ],
                "by_grade": {
                    label: LearningArea.get_subjects_for_grade(grade)
                    for grade, label in AcademicRecord.GRADE_CHOICES
                },
                # Pass selected year to context
                "academic_years": AcademicYear.objects.all().order_by("-start_date"),
                "selected_year": selected_year,
                "promoted_stats": list(promoted_stats),
            }
        )
        return context


def dashboard_stats_api(request):
    """
    API endpoint to get real-time dashboard statistics
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    # Get all students
    students = Student.objects.all()

    # Calculate counts for each status
    enrolled_count = students.filter(status="ENROLLED").count()
    transferred_count = students.filter(status="TRANSFERRED").count()
    dropped_count = students.filter(status="DROPPED").count()

    return JsonResponse(
        {
            "enrolled_count": enrolled_count,
            "transferred_count": transferred_count,
            "dropped_count": dropped_count,
        }
    )


def get_adviser_api(request):
    """
    API endpoint to get the adviser details for a given section
    """
    section_id = request.GET.get("section_id")
    if not section_id:
        return JsonResponse({"adviser_id": "", "adviser_name": ""})

    try:
        profile = TeacherProfile.objects.select_related("user").get(
            section_id=section_id
        )
        name = profile.user.get_full_name() or profile.user.username
        if profile.user.last_name and profile.user.first_name:
            name = f"{profile.user.last_name}, {profile.user.first_name}"
        return JsonResponse({"adviser_id": profile.user.id, "adviser_name": name})
    except TeacherProfile.DoesNotExist:
        return JsonResponse({"adviser_id": "", "adviser_name": ""})


def get_section_adviser_data_api(request):
    """
    API endpoint to get sections and advisers based on grade level
    """
    grade_level = request.GET.get("grade_level")

    if not grade_level:
        return JsonResponse({"sections": [], "advisers": []})

    # Get Sections
    sections = Section.objects.filter(grade_level=grade_level).values("id", "name")

    # Get Advisers (Teachers assigned to this grade level)
    # Filter TeacherProfile by grade_level, then get related User info
    profiles = TeacherProfile.objects.filter(grade_level=grade_level).select_related(
        "user", "section"
    )

    advisers = []
    for profile in profiles:
        user = profile.user
        name = user.get_full_name() or user.username
        if user.last_name and user.first_name:
            name = f"{user.last_name}, {user.first_name}"

        section_name = profile.section.name if profile.section else "No Section"
        display_name = f"{name} - Grade {profile.grade_level} - {section_name}"

        advisers.append({"id": user.id, "name": display_name})

    return JsonResponse({"sections": list(sections), "advisers": advisers})
