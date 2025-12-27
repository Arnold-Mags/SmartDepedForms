from django.views.generic import CreateView, UpdateView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.contrib import messages
from .models import (
    School,
    Student,
    AcademicRecord,
    SubjectGrade,
    LearningArea,
    Section,
    TeacherProfile,
)
from django.contrib.auth.models import User, Group
from .forms import (
    SchoolForm,
    StudentForm,
    AcademicRecordForm,
    SubjectGradeForm,
    LearningAreaForm,
    SectionForm,
    TeacherProfileForm,
    UserForm,
    SubjectGradeRemedialForm,
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


class RegistrarAccessMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.groups.filter(name="Registrar").exists() or user.is_superuser


class GradingAccessMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return (
            user.groups.filter(name__in=["Teacher", "Registrar"]).exists()
            or user.is_superuser
        )


class TeacherAccessMixin(GradingAccessMixin):
    """Keep for backward compatibility but use GradingAccessMixin for new views"""

    pass


class StudentCreateView(LoginRequiredMixin, RegistrarAccessMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = "student_form.html"
    success_url = reverse_lazy("teacher_dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Student added successfully.")
        return super().form_valid(form)


class StudentUpdateView(LoginRequiredMixin, RegistrarAccessMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = "student_form.html"
    success_url = reverse_lazy("teacher_dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Student updated successfully.")
        return super().form_valid(form)


class AcademicRecordCreateView(LoginRequiredMixin, RegistrarAccessMixin, CreateView):
    model = AcademicRecord
    form_class = AcademicRecordForm
    template_name = "academic_record_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Optional: pass student_pk to form if needed for logic
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial["student"] = self.kwargs.get("student_pk")
        # Pre-fill adviser if registrar is logged in?
        return initial

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


class LearningAreaListView(LoginRequiredMixin, GradingAccessMixin, ListView):
    model = LearningArea
    template_name = "learning_area_list.html"
    context_object_name = "learning_areas"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        by_grade = {}
        for grade, label in AcademicRecord.GRADE_CHOICES:
            by_grade[label] = LearningArea.get_subjects_for_grade(grade)
        context["by_grade"] = by_grade
        return context


class LearningAreaCreateView(LoginRequiredMixin, RegistrarAccessMixin, CreateView):
    model = LearningArea
    form_class = LearningAreaForm
    template_name = "learning_area_form.html"
    success_url = reverse_lazy("learning_area_list")

    def form_valid(self, form):
        messages.success(self.request, "Learning Area created successfully.")
        return super().form_valid(form)


class LearningAreaUpdateView(LoginRequiredMixin, RegistrarAccessMixin, UpdateView):
    model = LearningArea
    form_class = LearningAreaForm
    template_name = "learning_area_form.html"
    success_url = reverse_lazy("learning_area_list")

    def form_valid(self, form):
        messages.success(self.request, "Learning Area updated successfully.")
        return super().form_valid(form)


class LearningAreaDeleteView(LoginRequiredMixin, RegistrarAccessMixin, View):
    def post(self, request, pk):
        learning_area = get_object_or_404(LearningArea, pk=pk)
        learning_area.delete()
        messages.success(request, "Learning Area deleted successfully.")
        return redirect("learning_area_list")


# Academic Record Detail & Grades

from django.views.generic import DetailView


class AcademicRecordDetailView(LoginRequiredMixin, GradingAccessMixin, DetailView):
    model = AcademicRecord
    template_name = "academic_record_detail.html"
    context_object_name = "record"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get grades for the current view
        context["grades"] = SubjectGrade.objects.filter(
            academic_record=self.object
        ).select_related("learning_area")

        # Get ALL records for this student for the Transcript View
        # Stacked from newest to oldest
        context["all_records"] = (
            AcademicRecord.objects.filter(student=self.object.student)
            .order_by("-school_year", "-grade_level")
            .prefetch_related("subject_grades", "subject_grades__learning_area")
        )
        return context


class SubjectGradeUpdateView(LoginRequiredMixin, GradingAccessMixin, UpdateView):
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


class SubjectGradeDeleteView(LoginRequiredMixin, GradingAccessMixin, View):
    def post(self, request, pk):
        grade = get_object_or_404(SubjectGrade, pk=pk)
        record_id = grade.academic_record.pk
        grade.delete()
        messages.success(request, "Grade entry deleted.")
        return redirect("record_detail", pk=record_id)


# --- Section & Teacher Management (Registrar) ---


class SectionListView(LoginRequiredMixin, RegistrarAccessMixin, ListView):
    model = Section
    template_name = "section_list.html"
    context_object_name = "sections"


class SectionCreateView(LoginRequiredMixin, RegistrarAccessMixin, CreateView):
    model = Section
    form_class = SectionForm
    template_name = "section_form.html"
    success_url = reverse_lazy("section_list")

    def form_valid(self, form):
        messages.success(self.request, "Section created successfully.")
        return super().form_valid(form)


class SectionUpdateView(LoginRequiredMixin, RegistrarAccessMixin, UpdateView):
    model = Section
    form_class = SectionForm
    template_name = "section_form.html"
    success_url = reverse_lazy("section_list")


class TeacherCreateView(LoginRequiredMixin, RegistrarAccessMixin, View):
    template_name = "teacher_account_form.html"

    def get(self, request):
        user_form = UserForm()
        profile_form = TeacherProfileForm()
        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form},
        )

    def post(self, request):
        user_form = UserForm(request.POST)
        profile_form = TeacherProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data["password"])
            user.save()

            # Add to Teacher group
            teacher_group, _ = Group.objects.get_or_create(name="Teacher")
            user.groups.add(teacher_group)

            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()

            messages.success(request, "Teacher account created successfully.")
            return redirect("teacher_dashboard")

        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form},
        )


class TeacherListView(LoginRequiredMixin, RegistrarAccessMixin, ListView):
    model = TeacherProfile
    template_name = "teacher_list.html"
    context_object_name = "profiles"

    def get_queryset(self):
        return TeacherProfile.objects.select_related("user", "section").all()


class TeacherDetailView(LoginRequiredMixin, RegistrarAccessMixin, DetailView):
    model = TeacherProfile
    template_name = "teacher_profile_detail.html"
    context_object_name = "profile"


class TeacherUpdateView(LoginRequiredMixin, RegistrarAccessMixin, View):
    template_name = "teacher_account_form.html"

    def get(self, request, pk):
        profile = get_object_or_404(TeacherProfile, pk=pk)
        user_form = UserForm(instance=profile.user)
        # Handle password separately for security - don't show existing
        user_form.fields.pop("password")
        profile_form = TeacherProfileForm(instance=profile)
        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form, "is_update": True},
        )

    def post(self, request, pk):
        profile = get_object_or_404(TeacherProfile, pk=pk)
        user_form = UserForm(request.POST, instance=profile.user)
        user_form.fields.pop("password")
        profile_form = TeacherProfileForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Teacher account updated successfully.")
            return redirect("teacher_list")

        return render(
            request,
            self.template_name,
            {"user_form": user_form, "profile_form": profile_form, "is_update": True},
        )


# --- Academic Evaluation Actions ---


class AcademicRecordPromoteView(LoginRequiredMixin, GradingAccessMixin, View):
    def post(self, request, pk):
        record = get_object_or_404(AcademicRecord, pk=pk)

        # Logic to promote: set remark to PROMOTED and create next grade record
        record.remarks = "PROMOTED"
        record.save(update_fields=["remarks"])

        next_record = record.promote()

        if next_record:
            messages.success(
                request, f"Student promoted to Grade {next_record.grade_level}."
            )
            return redirect("record_detail", pk=next_record.pk)
        else:
            messages.success(request, "Student marked as PROMOTED/GRADUATED.")
            return redirect("record_detail", pk=record.pk)


class AcademicRecordRetainView(LoginRequiredMixin, GradingAccessMixin, View):
    def post(self, request, pk):
        record = get_object_or_404(AcademicRecord, pk=pk)
        record.retain()
        messages.warning(request, "Student marked as RETAINED for this grade level.")
        return redirect("record_detail", pk=record.pk)


class SubjectGradeRemedialUpdateView(
    LoginRequiredMixin, GradingAccessMixin, UpdateView
):
    model = SubjectGrade
    form_class = SubjectGradeRemedialForm
    template_name = "subject_grade_remedial_form.html"

    def get_success_url(self):
        return reverse_lazy(
            "record_detail", kwargs={"pk": self.object.academic_record.pk}
        )

    def form_valid(self, form):
        # The model's save() handles final rating recomputation via clean()
        messages.success(self.request, "Remedial information updated.")
        return super().form_valid(form)


# class AcademicRecordUpdateView(LoginRequiredMixin, RegistrarAccessMixin, UpdateView):
#    model = AcademicRecord
#    form_class = AcademicRecordForm
#    template_name = "academic_record_form.html"

#    def get_success_url(self):
#        return reverse_lazy("teacher_dashboard")

#    def form_valid(self, form):
#        messages.success(self.request, "Academic record updated successfully.")
#        return super().form_valid(form)


# --- Academic Year Management (Registrar Only) ---

from .forms import AcademicYearForm
from .models import AcademicYear


class AcademicYearListView(LoginRequiredMixin, RegistrarAccessMixin, ListView):
    model = AcademicYear
    template_name = "academic_year_list.html"
    context_object_name = "academic_years"


class AcademicYearCreateView(LoginRequiredMixin, RegistrarAccessMixin, CreateView):
    model = AcademicYear
    form_class = AcademicYearForm
    template_name = "academic_year_form.html"
    success_url = reverse_lazy("academic_year_list")

    def form_valid(self, form):
        messages.success(self.request, "Academic year created successfully.")
        return super().form_valid(form)


class AcademicYearUpdateView(LoginRequiredMixin, RegistrarAccessMixin, UpdateView):
    model = AcademicYear
    form_class = AcademicYearForm
    template_name = "academic_year_form.html"
    success_url = reverse_lazy("academic_year_list")

    def form_valid(self, form):
        messages.success(self.request, "Academic year updated successfully.")
        return super().form_valid(form)


class AcademicRecordUpdateView(LoginRequiredMixin, TeacherAccessMixin, UpdateView):
    model = AcademicRecord
    form_class = AcademicRecordForm
    template_name = "academic_record_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Academic record updated successfully.")
        return super().form_valid(form)

    # def get_success_url(self):
    #    return reverse_lazy('record_detail', kwargs={'pk': self.object.pk})
    def get_success_url(self):
        return reverse_lazy("teacher_dashboard")
