from django.views.generic import CreateView, UpdateView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from .models import School, Student, AcademicRecord, SubjectGrade, LearningArea
from .forms import (
    SchoolForm,
    StudentForm,
    AcademicRecordForm,
    SubjectGradeForm,
    LearningAreaForm,
)

# --- Principal Views ---


class SchoolUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = School
    form_class = SchoolForm
    template_name = "school_form.html"
    success_url = reverse_lazy("principal_dashboard")

    def get_object(self, queryset=None):
        # Enforce singleton pattern logic for simplicity: get the first school or create one
        obj = School.objects.first()
        if not obj:
            # Create a default placeholder if none exists
            obj = School.objects.create(
                school_id="123456", name="Default School", address="Address"
            )
        return obj

    def test_func(self):
        return (
            self.request.user.groups.filter(name="Principal").exists()
            or self.request.user.is_superuser
        )

    def form_valid(self, form):
        messages.success(self.request, "School profile updated successfully.")
        return super().form_valid(form)


# --- Teacher Views ---


class TeacherAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user.groups.filter(name="Teacher").exists()
            or self.request.user.is_superuser
        )


class StudentCreateView(LoginRequiredMixin, TeacherAccessMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = "student_form.html"
    success_url = reverse_lazy("teacher_dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Student added successfully.")
        return super().form_valid(form)


class StudentUpdateView(LoginRequiredMixin, TeacherAccessMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = "student_form.html"
    success_url = reverse_lazy("teacher_dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Student updated successfully.")
        return super().form_valid(form)


class AcademicRecordCreateView(LoginRequiredMixin, TeacherAccessMixin, CreateView):
    model = AcademicRecord
    form_class = AcademicRecordForm
    template_name = "academic_record_form.html"

    def get_initial(self):
        return {"student": self.kwargs.get("student_pk")}

    def form_valid(self, form):
        form.instance.student_id = self.kwargs.get("student_pk")
        messages.success(self.request, "Academic record created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "teacher_dashboard"
        )  # Ideally redirect to record detail/grades


class SubjectGradeCreateView(LoginRequiredMixin, TeacherAccessMixin, CreateView):
    model = SubjectGrade
    form_class = SubjectGradeForm
    template_name = "subject_grade_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Get the academic record to determine grade level
        record_id = self.kwargs.get("record_pk")
        record = get_object_or_404(AcademicRecord, pk=record_id)
        kwargs["grade_level"] = record.grade_level
        return kwargs

    def form_valid(self, form):
        form.instance.academic_record_id = self.kwargs.get("record_pk")
        try:
            return super().form_valid(form)
        except Exception:  # Catch IntegrityError or other db errors
            form.add_error(
                "learning_area", "This subject already exists for this record."
            )
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy(
            "record_detail", kwargs={"pk": self.kwargs.get("record_pk")}
        )


# Learning Area Views


class LearningAreaListView(LoginRequiredMixin, TeacherAccessMixin, ListView):
    model = LearningArea
    template_name = "learning_area_list.html"
    context_object_name = "learning_areas"


class LearningAreaCreateView(LoginRequiredMixin, TeacherAccessMixin, CreateView):
    model = LearningArea
    form_class = LearningAreaForm
    template_name = "learning_area_form.html"
    success_url = reverse_lazy("learning_area_list")

    def form_valid(self, form):
        messages.success(self.request, "Learning Area created successfully.")
        return super().form_valid(form)


class LearningAreaUpdateView(LoginRequiredMixin, TeacherAccessMixin, UpdateView):
    model = LearningArea
    form_class = LearningAreaForm
    template_name = "learning_area_form.html"
    success_url = reverse_lazy("learning_area_list")

    def form_valid(self, form):
        messages.success(self.request, "Learning Area updated successfully.")
        return super().form_valid(form)


class LearningAreaDeleteView(LoginRequiredMixin, TeacherAccessMixin, View):
    def post(self, request, pk):
        learning_area = get_object_or_404(LearningArea, pk=pk)
        learning_area.delete()
        messages.success(request, "Learning Area deleted successfully.")
        return redirect("learning_area_list")


# Academic Record Detail & Grades

from django.views.generic import DetailView


class AcademicRecordDetailView(LoginRequiredMixin, TeacherAccessMixin, DetailView):
    model = AcademicRecord
    template_name = "academic_record_detail.html"
    context_object_name = "record"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get grades for this record
        context["grades"] = SubjectGrade.objects.filter(academic_record=self.object)
        return context


class SubjectGradeUpdateView(LoginRequiredMixin, TeacherAccessMixin, UpdateView):
    model = SubjectGrade
    form_class = SubjectGradeForm
    template_name = "subject_grade_form.html"

    def get_success_url(self):
        return reverse_lazy(
            "record_detail", kwargs={"pk": self.object.academic_record.pk}
        )

    def form_valid(self, form):
        messages.success(self.request, "Grade updated successfully.")
        return super().form_valid(form)


class SubjectGradeDeleteView(LoginRequiredMixin, TeacherAccessMixin, View):
    def post(self, request, pk):
        grade = get_object_or_404(SubjectGrade, pk=pk)
        record_id = grade.academic_record.pk
        grade.delete()
        messages.success(request, "Grade entry deleted.")
        return redirect("record_detail", pk=record_id)
