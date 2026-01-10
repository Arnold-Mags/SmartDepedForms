import os
import django
import sys
from datetime import date

# Setup Django
sys.path.append("c:\\Users\\ARNOLD\\Documents\\GitHub\\SmartDepedForms\\SmartForms")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SmartForms.settings")
django.setup()

from depedsfportal.models import Student, AcademicRecord, AcademicYear, School, Section
from depedsfportal.forms import StudentForm


def reproduce_issue():
    print("Starting reproduction...")

    # 1. Get Current Year
    current_year = AcademicYear.get_current_year()
    print(f"Current Year: {current_year}")

    if not current_year:
        print("ERROR: No current year found!")
        return

    # 2. Get/Create School
    school = School.objects.first()
    if not school:
        school = School.objects.create(
            school_id="123456", name="Default School", address="Address"
        )
    print(f"School: {school}")

    # 3. Create a Test Student (mimic form data)
    # We use a unique LRN to avoid collision
    test_lrn = "999999999999"
    # Cleanup previous run
    Student.objects.filter(lrn=test_lrn).delete()

    student_data = {
        "lrn": test_lrn,
        "first_name": "Test",
        "last_name": "Student",
        "birthdate": date(2010, 1, 1),
        "sex": "M",
        "grade_level": 7,  # Simulated form field
        # 'section': None, # Optional
    }

    print("Creating Student...")
    try:
        student = Student.objects.create(
            lrn=student_data["lrn"],
            first_name=student_data["first_name"],
            last_name=student_data["last_name"],
            birthdate=student_data["birthdate"],
            sex=student_data["sex"],
        )
        print(f"Student created: {student}")
    except Exception as e:
        print(f"Failed to create student: {e}")
        return

    # 4. Attempt AcademicRecord creation (Logic from views_forms.py)
    grade_level = student_data["grade_level"]
    section = None  # Simulating empty section

    print(f"Attempting to create AcademicRecord for Year {current_year.year_label}...")
    try:
        record = AcademicRecord.objects.create(
            student=student,
            school=school,
            grade_level=grade_level,
            section=section,  # This is valid (nullable)
            school_year=current_year.year_label,
        )
        print(f"SUCCESS: AcademicRecord created: {record}")
    except Exception as e:
        print(f"FAILURE: Failed to create AcademicRecord!")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    reproduce_issue()
