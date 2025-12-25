from django import forms
from .models import School, Student, AcademicRecord, SubjectGrade, LearningArea
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
