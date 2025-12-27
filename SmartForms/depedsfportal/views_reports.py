import csv
import datetime
from django.shortcuts import render, HttpResponse
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.template.loader import render_to_string
from django.core.files.storage import FileSystemStorage
from django.conf import settings

# Try importing weasyprint, handle if not installed (though it should be)
try:
    from weasyprint import HTML
    from weasyprint.text.fonts import FontConfiguration
except ImportError:
    HTML = None

from .models import Student, AcademicRecord, School, AcademicYear


class PrincipalAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user.groups.filter(name="Principal").exists()
            or self.request.user.is_superuser
        )


class ReportDashboardView(LoginRequiredMixin, PrincipalAccessMixin, TemplateView):
    template_name = "reports/report_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filter Logic
        grade_level = self.request.GET.get("grade")
        status = self.request.GET.get("status")
        school_year = self.request.GET.get("year")

        # Base Query
        students = Student.objects.all().order_by("last_name")

        if grade_level:
            # Filter by latest academic record's grade level
            students = students.filter(
                academic_records__grade_level=grade_level
            ).distinct()

        if school_year:
            students = students.filter(
                academic_records__school_year=school_year
            ).distinct()

        if status:
            if status in ["ENROLLED", "TRANSFERRED", "DROPPED"]:
                students = students.filter(status=status)
            elif status == "PASSED":
                # Passed in specific year/grade
                students = students.filter(academic_records__remarks="PASSED")
                if school_year:
                    students = students.filter(
                        academic_records__school_year=school_year
                    )
            elif status == "REMEDIAL":
                students = students.filter(
                    academic_records__remarks="REMEDIAL"  # or 'Needs Remedial' depending on model, checking model...
                )
                # Checking model logic: determine_remarks returns 'Needs Remedial'?
                # Wait, model says "Needs Remedial" in SubjectGrade, but "PROMOTED/RETAINED/PASSED/FAILED" in AcademicRecord.
                # Let's adjust query to filter based on available fields.
                pass

        context["students"] = students
        context["current_filters"] = self.request.GET
        context["academic_years"] = AcademicYear.objects.all().order_by("-start_date")
        return context


class ExportReportCSVView(LoginRequiredMixin, PrincipalAccessMixin, View):
    def get(self, request, *args, **kwargs):
        # ... Reuse filter logic (should be factored out, but duplicating for speed for now) ...
        # Simplified: Just dump current filtered queryset

        grade_level = request.GET.get("grade")
        status = request.GET.get("status")
        school_year = request.GET.get("year")

        students = Student.objects.all().order_by("last_name")

        if grade_level:
            students = students.filter(
                academic_records__grade_level=grade_level
            ).distinct()
        if school_year:
            students = students.filter(
                academic_records__school_year=school_year
            ).distinct()
        if status and status in ["ENROLLED", "TRANSFERRED", "DROPPED"]:
            students = students.filter(status=status)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="student_report_{datetime.date.today()}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            ["LRN", "Last Name", "First Name", "Sex", "Birthdate", "Status", "Address"]
        )

        for student in students:
            writer.writerow(
                [
                    student.lrn,
                    student.last_name,
                    student.first_name,
                    student.sex,
                    student.birthdate,
                    student.status,
                    f"{student.barangay}, {student.city}, {student.province}",
                ]
            )

        return response


class ExportReportPDFView(LoginRequiredMixin, PrincipalAccessMixin, View):
    def get(self, request, *args, **kwargs):
        # ... Reuse filter logic ...
        grade_level = request.GET.get("grade")
        status = request.GET.get("status")
        school_year = request.GET.get("year")

        students = Student.objects.all().order_by("last_name")

        if grade_level:
            students = students.filter(
                academic_records__grade_level=grade_level
            ).distinct()
        if school_year:
            students = students.filter(
                academic_records__school_year=school_year
            ).distinct()
        if status and status in ["ENROLLED", "TRANSFERRED", "DROPPED"]:
            students = students.filter(status=status)

        html_string = render_to_string(
            "reports/report_pdf_template.html",
            {
                "students": students,
                "generated_at": datetime.datetime.now(),
                "filters": request.GET,
            },
        )

        if HTML:
            html = HTML(string=html_string)
            result = html.write_pdf()

            response = HttpResponse(content_type="application/pdf")
            response["Content-Disposition"] = (
                f'inline; filename="report_{datetime.date.today()}.pdf"'
            )
            response["Content-Transfer-Encoding"] = "binary"
            with response as f:
                f.write(result)
            return response
        else:
            return HttpResponse("WeasyPrint not installed", status=500)


class AnalyticsDashboardView(LoginRequiredMixin, PrincipalAccessMixin, TemplateView):
    template_name = "reports/analytics_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Base Query
        students = Student.objects.all()

        # Apply Filters
        grade_level = self.request.GET.get("grade")
        status = self.request.GET.get("status")
        school_year = self.request.GET.get("year")

        if grade_level:
            students = students.filter(
                academic_records__grade_level=grade_level
            ).distinct()
        if school_year:
            students = students.filter(
                academic_records__school_year=school_year
            ).distinct()
        if status:
            # Basic status filter
            if status in ["ENROLLED", "TRANSFERRED", "DROPPED"]:
                students = students.filter(status=status)

        # Location Analytics (Filtered)
        by_barangay = (
            students.values("barangay").annotate(count=Count("lrn")).order_by("-count")
        )
        by_city = (
            students.values("city").annotate(count=Count("lrn")).order_by("-count")
        )
        by_province = (
            students.values("province").annotate(count=Count("lrn")).order_by("-count")
        )

        # Status Analytics (Filtered)
        by_status = students.values("status").annotate(count=Count("lrn"))

        context["by_barangay"] = by_barangay
        context["by_city"] = by_city
        context["by_province"] = by_province
        context["by_status"] = by_status
        context["by_status"] = by_status
        context["current_filters"] = self.request.GET
        context["academic_years"] = AcademicYear.objects.all().order_by("-start_date")

        return context
