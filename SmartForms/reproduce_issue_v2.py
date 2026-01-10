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
    print("Starting reproduction (Exact Form Data Simulation)...")

    current_year = AcademicYear.get_current_year()
    if not current_year:
        return

    school = School.objects.first()

    # Clean previous test
    test_lrn = "888888888888"
    Student.objects.filter(lrn=test_lrn).delete()

    # Create Student
    student = Student.objects.create(
        lrn=test_lrn,
        first_name="TestString",
        last_name="Student",
        birthdate=date(2010, 1, 1),
        sex="M",
    )

    # 4. Attempt AcademicRecord creation with STRING grade_level
    # Form data comes as string "7"
    grade_level = "7"
    section = None

    print(
        f"Attempting to create AcademicRecord with grade_level='{grade_level}' (type: {type(grade_level)})..."
    )

    try:
        record = AcademicRecord.objects.create(
            student=student,
            school=school,
            grade_level=grade_level,  # STRING PASSED HERE
            section=section,
            school_year=current_year.year_label,
        )
        print(f"SUCCESS: AcademicRecord created: {record}")
        print(f"Record grade_level type in DB: {type(record.grade_level)}")

    except Exception as e:
        print(f"FAILURE: Failed to create AcademicRecord!")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    reproduce_issue()
