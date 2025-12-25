from depedsfportal.models import AcademicRecord

def fix_grades():
    # Map old index (1-4) to new grade levels (7-10)
    updates = {
        1: 7,
        2: 8,
        3: 9, 
        4: 10
    }
    
    count = 0
    for old, new in updates.items():
        rows = AcademicRecord.objects.filter(grade_level=old).update(grade_level=new)
        count += rows
        print(f"Updated {rows} records from Grade {old} to Grade {new}")
    
    print(f"Total records updated: {count}")

if __name__ == '__main__':
    fix_grades()
