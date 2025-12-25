from django.contrib import admin
from .models import Student, School, AcademicRecord, LearningArea, SubjectGrade

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('lrn', 'get_full_name', 'sex', 'birthdate', 'credential_presented')
    list_filter = ('sex', 'credential_presented', 'created_at')
    search_fields = ('lrn', 'first_name', 'last_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('lrn', 'first_name', 'middle_name', 'last_name', 'name_extension', 'birthdate', 'sex')
        }),
        ('Enrollment Eligibility', {
            'fields': ('credential_presented', 'other_credential', 'pept_rating', 'pept_date', 'pept_testing_center')
        }),
        ('Address Information', {
            'fields': ('country', 'region', 'province', 'city', 'barangay', 'address_line1')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('school_id', 'name', 'district', 'division', 'region')
    list_filter = ('division', 'region', 'district')
    search_fields = ('school_id', 'name', 'district')
    
    fieldsets = (
        ('School Information', {
            'fields': ('school_id', 'name', 'address')
        }),
        ('Location', {
            'fields': ('district', 'division', 'region')
        }),
    )


@admin.register(LearningArea)
class LearningAreaAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'applicable_grades', 'is_core', 'is_optional', 'order')
    list_filter = ('applicable_grades', 'is_core', 'is_optional')
    search_fields = ('code', 'name')
    ordering = ('order', 'name')


class SubjectGradeInline(admin.TabularInline):
    model = SubjectGrade
    extra = 0
    readonly_fields = ('final_rating', 'created_at', 'updated_at')
    fields = ('learning_area', 'quarter_1', 'quarter_2', 'quarter_3', 'quarter_4', 'final_rating', 'needs_remedial', 'remarks')


@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'grade_level', 'school_year', 'general_average', 'remarks')
    list_filter = ('grade_level', 'school_year', 'remarks', 'school')
    search_fields = ('student__lrn', 'student__first_name', 'student__last_name')
    readonly_fields = ('general_average', 'remarks', 'created_at', 'updated_at')
    inlines = [SubjectGradeInline]
    
    fieldsets = (
        ('Student & School Information', {
            'fields': ('student', 'school', 'grade_level', 'section', 'school_year', 'adviser_teacher')
        }),
        ('Computed Results', {
            'fields': ('general_average', 'remarks')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SubjectGrade)
class SubjectGradeAdmin(admin.ModelAdmin):
    list_display = ('academic_record', 'learning_area', 'final_rating', 'needs_remedial', 'remarks')
    list_filter = ('needs_remedial', 'learning_area__applicable_grades', 'academic_record__school_year')
    search_fields = ('academic_record__student__lrn', 'learning_area__name')
    readonly_fields = ('final_rating', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Subject Information', {
            'fields': ('academic_record', 'learning_area')
        }),
        ('Quarterly Ratings', {
            'fields': ('quarter_1', 'quarter_2', 'quarter_3', 'quarter_4')
        }),
        ('Final Rating', {
            'fields': ('final_rating', 'needs_remedial', 'remarks')
        }),
        ('Remedial Information', {
            'fields': ('remedial_conducted_from', 'remedial_conducted_to', 'remedial_mark', 'recomputed_final_grade'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )