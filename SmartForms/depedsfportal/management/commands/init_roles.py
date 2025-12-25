from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from depedsfportal.models import Student, AcademicRecord, SubjectGrade, LearningArea

class Command(BaseCommand):
    help = 'Initialize User Roles and Permissions'

    def handle(self, *args, **kwargs):
        # Create Groups
        teacher_group, created = Group.objects.get_or_create(name='Teacher')
        principal_group, created = Group.objects.get_or_create(name='Principal')
        
        self.stdout.write(self.style.SUCCESS('Groups created/verified.'))

        # Teacher Permissions
        # Can view, add, change students, records, grades. 
        # Cannot delete students.
        
        models_to_grant = [Student, AcademicRecord, SubjectGrade, LearningArea]
        
        teacher_permissions = []
        for model in models_to_grant:
            content_type = ContentType.objects.get_for_model(model)
            # Filter for add, change, view. Exclude delete.
            perms = Permission.objects.filter(
                content_type=content_type, 
                codename__regex=r'^(add|change|view)_'
            )
            teacher_permissions.extend(perms)
            
        teacher_group.permissions.set(teacher_permissions)
        self.stdout.write(self.style.SUCCESS('Teacher permissions assigned (No Delete).'))

        # Principal Permissions
        # Can Configure School (Full Access).
        # View-only for Student data.
        
        # 1. School Model - Full Access
        from depedsfportal.models import School
        school_ct = ContentType.objects.get_for_model(School)
        school_perms = Permission.objects.filter(content_type=school_ct)
        
        # 2. Student Data - View Only
        view_perms = []
        for model in models_to_grant:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=content_type, codename__startswith='view_')
            view_perms.extend(perms)
            
        principal_permissions = list(school_perms) + list(view_perms)
            
        principal_group.permissions.set(principal_permissions)
        self.stdout.write(self.style.SUCCESS('Principal permissions assigned (School Config + Read-only Data).'))
        
        self.stdout.write(self.style.SUCCESS('Successfully initialized roles.'))
