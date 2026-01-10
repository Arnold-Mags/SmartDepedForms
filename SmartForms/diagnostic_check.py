import os
import django
import sys

# Setup Django
sys.path.append("c:\\Users\\ARNOLD\\Documents\\GitHub\\SmartDepedForms\\SmartForms")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SmartForms.settings")
django.setup()

from depedsfportal.models import Student, AcademicRecord, AcademicYear

print(f"Current Year from helper: {AcademicYear.get_current_year()}")
print("All Academic Years:")
for ay in AcademicYear.objects.all():
    print(
        f"  {ay.year_label} (Current: {ay.is_current}, Start: {ay.start_date}, End: {ay.end_date})"
    )

print("\nRecent Students (Last 5):")
for s in Student.objects.order_by("-created_at")[:5]:
    print(
        f"ID: {s.pk}, LRN: {s.lrn}, Name: {s.get_full_name()}, Created: {s.created_at}"
    )
    records = AcademicRecord.objects.filter(student=s)
    print(f"  Records count: {records.count()}")
    for r in records:
        print(
            f"    - SY: {r.school_year}, Grade: {r.grade_level}, Section: {r.section}"
        )

print("\nCheck finished.")
