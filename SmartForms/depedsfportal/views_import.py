import csv
import io
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from .models import Student


class StudentImportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View to handle bulk import of Students via CSV"""

    def test_func(self):
        # Allow both teachers and principals
        return self.request.user.groups.filter(
            name__in=["Teacher", "Principal"]
        ).exists()

    def get(self, request):
        if "download_template" in request.GET:
            return self.download_template()
        return render(request, "import_students.html")

    def post(self, request):
        csv_file = request.FILES.get("csv_file")

        if not csv_file:
            messages.error(request, "Please select a CSV file to upload.")
            return redirect("student_import")

        if not csv_file.name.endswith(".csv"):
            messages.error(request, "File is not a CSV. Please upload a .csv file.")
            return redirect("student_import")

        # Process CSV
        try:
            data_set = csv_file.read().decode("UTF-8")
            io_string = io.StringIO(data_set)
            next(io_string)  # Skip header

            created_count = 0
            updated_count = 0
            errors = []

            for row in csv.reader(io_string, delimiter=",", quotechar='"'):
                # Expected format: LRN, Last Name, First Name, Middle Name, Sex, Birthdate (YYYY-MM-DD)
                # Optional: Address, Status

                # Check for minimum columns
                if len(row) < 6:
                    continue

                lrn = row[0].strip()
                last_name = row[1].strip()
                first_name = row[2].strip()
                middle_name = row[3].strip()
                sex = row[4].strip().upper()
                birthdate_str = row[5].strip()

                # Basic validation
                if not lrn or not last_name or not first_name:
                    continue

                try:
                    birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d").date()
                except ValueError:
                    errors.append(f"Invalid date for {last_name}: {birthdate_str}")
                    continue

                if sex not in ["M", "F"]:
                    sex = "M"  # Default or skip?

                # Create or Update
                student, created = Student.objects.update_or_create(
                    lrn=lrn,
                    defaults={
                        "last_name": last_name,
                        "first_name": first_name,
                        "middle_name": middle_name,
                        "sex": sex,
                        "birthdate": birthdate,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            messages.success(
                request,
                f"Import Complete. Created: {created_count}, Updated: {updated_count}",
            )
            if errors:
                messages.warning(request, f"Errors: {', '.join(errors[:5])}...")

            return redirect("teacher_dashboard")

        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")
            return redirect("student_import")

    def download_template(self):
        """Generate a CSV template"""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="student_import_template.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "LRN",
                "Last Name",
                "First Name",
                "Middle Name",
                "Sex (M/F)",
                "Birthdate (YYYY-MM-DD)",
            ]
        )
        writer.writerow(["100001", "Dela Cruz", "Juan", "Santos", "M", "2010-01-31"])

        return response
