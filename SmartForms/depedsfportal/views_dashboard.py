from django.views.generic import TemplateView, ListView, RedirectView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.db.models import Count, Avg, Q
from django.http import JsonResponse
from .models import Student, AcademicRecord, SubjectGrade, LearningArea


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

        # Registrar and Superuser see all students
        if user.is_superuser or user.groups.filter(name="Registrar").exists():
            return qs.order_by("last_name", "first_name")

        # Teachers only see students in their advisory
        try:
            profile = user.teacher_profile
            # Filter students who have an academic record in the teacher's grade and section
            # We assume the current or latest academic record
            return (
                qs.filter(
                    academic_records__grade_level=profile.grade_level,
                    academic_records__section=profile.section,
                )
                .distinct()
                .order_by("last_name", "first_name")
            )
        except Exception:
            # If no profile, they see no students (or maybe we show an error)
            return Student.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all students for the table
        students = self.get_queryset()
        context["students"] = students

        # Calculate counts for each status
        enrolled_count = students.filter(status="ENROLLED").count()
        transferred_count = students.filter(status="TRANSFERRED").count()
        dropped_count = students.filter(status="DROPPED").count()

        context.update(
            {
                "enrolled_count": enrolled_count,
                "transferred_count": transferred_count,
                "dropped_count": dropped_count,
            }
        )

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

        # Summary Statistics
        total_students = Student.objects.count()

        # Status Stats
        enrolled_count = Student.objects.filter(status="ENROLLED").count()
        transferred_count = Student.objects.filter(status="TRANSFERRED").count()
        dropped_count = Student.objects.filter(status="DROPPED").count()

        # Performance Stats (Sample logic - can be refined)
        # Count passed vs failed/retained in latest records
        latest_records = AcademicRecord.objects.filter(
            school_year="2024-2025"
        )  # Assuming current SY

        passed_count = latest_records.filter(remarks="PASSED").count()
        promoted_count = latest_records.filter(remarks="PROMOTED").count()
        failed_count = latest_records.filter(remarks="FAILED").count()
        retained_count = latest_records.filter(remarks="RETAINED").count()

        context.update(
            {
                "total_students": total_students,
                "enrolled_count": enrolled_count,
                "transferred_count": transferred_count,
                "dropped_count": dropped_count,
                "passed_count": passed_count + promoted_count,
                "failed_count": failed_count + retained_count,
                # Chart Data: Enrollment by Grade (Current SY)
                "enrollment_by_grade": list(
                    AcademicRecord.objects.filter(
                        school_year="2024-2025"  # Hardcoded for demo, ideally dynamic
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
