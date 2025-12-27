from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.template.loader import render_to_string
from .models import Student, AcademicRecord, School
import datetime

try:
    from weasyprint import HTML
    from weasyprint.text.fonts import FontConfiguration
except ImportError:
    HTML = None


class TeacherAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user.groups.filter(name__in=["Teacher", "Registrar"]).exists()
            or self.request.user.is_superuser
        )


class SF10PrintView(LoginRequiredMixin, TeacherAccessMixin, View):
    """Generate SF10-JHS PDF for a specific student"""

    def get(self, request, lrn):
        student = get_object_or_404(Student, lrn=lrn)
        school = School.objects.first()

        # Get all academic records for the student, ordered by school year
        academic_records = AcademicRecord.objects.filter(student=student).order_by(
            "school_year", "grade_level"
        )

        # Group records by page (4 records per page based on SF10 layout)
        records_per_page = 4
        pages = []
        for i in range(0, len(academic_records), records_per_page):
            pages.append(academic_records[i : i + records_per_page])

        context = {
            "student": student,
            "school": school,
            "pages": pages,
            "generated_date": datetime.date.today(),
        }

        # Render HTML template
        html_string = render_to_string("sf10_print_template.html", context)

        if HTML:
            # Generate PDF
            font_config = FontConfiguration()
            # Use request.build_absolute_uri('/') as base_url if available, or static root
            base_url = request.build_absolute_uri("/")
            html = HTML(string=html_string, base_url=base_url)
            result = html.write_pdf(font_config=font_config)

            # Return PDF response
            response = HttpResponse(content_type="application/pdf")
            response["Content-Disposition"] = (
                f'inline; filename="SF10_{student.lrn}_{datetime.date.today()}.pdf"'
            )
            response.write(result)
            return response
        else:
            return HttpResponse("WeasyPrint not installed", status=500)


class SF10PreviewView(LoginRequiredMixin, TeacherAccessMixin, View):
    """Preview SF10 in HTML format (for testing/debugging)"""

    def get(self, request, lrn):
        student = get_object_or_404(Student, lrn=lrn)
        school = School.objects.first()

        academic_records = AcademicRecord.objects.filter(student=student).order_by(
            "school_year", "grade_level"
        )

        # Group records by page
        records_per_page = 4
        pages = []
        for i in range(0, len(academic_records), records_per_page):
            pages.append(academic_records[i : i + records_per_page])

        context = {
            "student": student,
            "school": school,
            "pages": pages,
            "generated_date": datetime.date.today(),
        }

        return render(request, "sf10_print_template.html", context)
