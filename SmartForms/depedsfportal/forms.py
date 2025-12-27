from django import forms
from .models import (
    School,
    Student,
    AcademicRecord,
    SubjectGrade,
    LearningArea,
    Section,
    TeacherProfile,
    AcademicYear,
)
from django.contrib.auth.models import User
from django.forms import inlineformset_factory


class TailwindFormMixin:
    """Mixin to add Tailwind classes to form fields"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = (
                    "h-4 w-4 text-deped-blue focus:ring-deped-blue border-gray-300 rounded"
                )
            else:
                field.widget.attrs["class"] = (
                    "mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-deped-blue focus:border-deped-blue sm:text-sm"
                )


class SchoolForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = School
        fields = "__all__"


class StudentForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Student
        fields = "__all__"
        widgets = {
            "birthdate": forms.DateInput(attrs={"type": "date"}),
            "pept_date": forms.DateInput(attrs={"type": "date"}),
        }


class AcademicRecordForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = AcademicRecord
        exclude = ["created_at", "updated_at", "general_average", "remarks"]
        # student is handled in view (hidden or preset)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["section"].queryset = Section.objects.all()
        # Filter advisers to only show users in the Teacher group
        self.fields["adviser_teacher"].queryset = User.objects.filter(
            groups__name="Teacher"
        )

        # Custom label for adviser to show Grade and Section
        def adviser_label(obj):
            try:
                if hasattr(obj, "teacher_profile"):
                    profile = obj.teacher_profile
                    section_name = (
                        profile.section.name if profile.section else "No Section"
                    )
                    return f"{obj.last_name}, {obj.first_name} - Grade {profile.grade_level} - {section_name}"
            except Exception:
                pass
            return f"{obj.last_name}, {obj.first_name}"

        self.fields["adviser_teacher"].label_from_instance = adviser_label
        self.fields["adviser_teacher"].label = "Adviser Teacher"

        # Populate school_year dropdown with AcademicYear objects
        academic_years = AcademicYear.objects.all().order_by("-start_date")
        year_choices = [(year.year_label, year.year_label) for year in academic_years]

        # If no academic years exist, provide a fallback or allow free text (optional, but better to force config)
        if not year_choices:
            # Fallback for when no academic years are configured yet
            pass
        else:
            self.fields["school_year"].widget = forms.Select(choices=year_choices)

        # Pre-fill school_year with current academic year if creating new record
        if not self.instance.pk:
            current_year = AcademicYear.get_current_year()
            if current_year:
                self.fields["school_year"].initial = current_year.year_label


class SubjectGradeForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = SubjectGrade
        fields = ["learning_area", "quarter_1", "quarter_2", "quarter_3", "quarter_4"]

    def __init__(self, *args, **kwargs):
        grade_level = kwargs.pop("grade_level", None)
        super().__init__(*args, **kwargs)
        if grade_level:
            self.fields["learning_area"].queryset = LearningArea.get_subjects_for_grade(
                grade_level
            )


class LearningAreaForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = LearningArea
        fields = "__all__"


class SectionForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Section
        fields = "__all__"


class TeacherProfileForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = TeacherProfile
        fields = ["grade_level", "section"]


class UserForm(TailwindFormMixin, forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password"]


class SubjectGradeRemedialForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = SubjectGrade
        fields = [
            "remedial_conducted_from",
            "remedial_conducted_to",
            "remedial_mark",
            "remarks",
        ]
        widgets = {
            "remedial_conducted_from": forms.DateInput(attrs={"type": "date"}),
            "remedial_conducted_to": forms.DateInput(attrs={"type": "date"}),
        }


class AcademicYearForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ["year_label", "start_date", "end_date", "is_current"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }
