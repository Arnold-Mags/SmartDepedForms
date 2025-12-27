from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from depedsfportal.models import Student, AcademicRecord, SubjectGrade, LearningArea


class Command(BaseCommand):
    help = "Initialize User Roles and Permissions"

    def handle(self, *args, **kwargs):
        # Create Groups
        teacher_group, created = Group.objects.get_or_create(name="Teacher")
        registrar_group, created = Group.objects.get_or_create(name="Registrar")
        principal_group, created = Group.objects.get_or_create(name="Principal")

        self.stdout.write(self.style.SUCCESS("Groups created/verified."))

        # Registrar Permissions
        # Full access to Student data, plus Section and TeacherProfile.
        from depedsfportal.models import Section, TeacherProfile
        from django.contrib.auth.models import User

        registrar_models = [
            Student,
            AcademicRecord,
            SubjectGrade,
            LearningArea,
            Section,
            TeacherProfile,
            User,
        ]
        registrar_permissions = []
        for model in registrar_models:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=content_type)
            registrar_permissions.extend(perms)

        registrar_group.permissions.set(registrar_permissions)
        self.stdout.write(
            self.style.SUCCESS(
                "Registrar permissions assigned (Full Access to Student Data & Config)."
            )
        )

        # Teacher Permissions
        # Can view students and records.
        # Can view and change grades.

        teacher_view_models = [Student, AcademicRecord, LearningArea]
        teacher_change_models = [SubjectGrade]

        teacher_permissions = []
        for model in teacher_view_models:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(
                content_type=content_type, codename__startswith="view_"
            )
            teacher_permissions.extend(perms)

        for model in teacher_change_models:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(
                content_type=content_type, codename__regex=r"^(view|change|add)_"
            )
            teacher_permissions.extend(perms)

        teacher_group.permissions.set(teacher_permissions)
        self.stdout.write(
            self.style.SUCCESS("Teacher permissions assigned (No Delete).")
        )

        # Principal Permissions
        # Can Configure School (Full Access).
        # View-only for Student data.

        # 1. School Model - Full Access
        from depedsfportal.models import School

        school_ct = ContentType.objects.get_for_model(School)
        school_perms = Permission.objects.filter(content_type=school_ct)

        # 2. Student Data - View Only
        view_perms = []
        models_to_view = [Student, AcademicRecord, SubjectGrade, LearningArea]
        for model in models_to_view:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(
                content_type=content_type, codename__startswith="view_"
            )
            view_perms.extend(perms)

        principal_permissions = list(school_perms) + list(view_perms)

        principal_group.permissions.set(principal_permissions)
        self.stdout.write(
            self.style.SUCCESS(
                "Principal permissions assigned (School Config + Read-only Data)."
            )
        )

        self.stdout.write(self.style.SUCCESS("Successfully initialized roles."))
