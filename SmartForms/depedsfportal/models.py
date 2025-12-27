from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class Student(models.Model):
    """Student master record with LRN as primary key"""

    SEX_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
    ]

    CREDENTIAL_CHOICES = [
        ("KINDER_PROGRESS", "Kinder Progress Report"),
        ("ECCD_CHECKLIST", "ECCD Checklist"),
        ("KINDER_CERTIFICATE", "Kindergarten Certificate of Completion"),
        ("PEPT", "PEPT Passer"),
        ("OTHER", "Other Credential"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ENROLLED", "Enrolled"),
        ("TRANSFERRED", "Transferred Out"),
        ("DROPPED", "Dropped"),
        ("GRADUATED", "Graduated"),
    ]

    lrn = models.CharField(
        max_length=12, primary_key=True, verbose_name="Learner Reference Number"
    )
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    name_extension = models.CharField(
        max_length=10, blank=True, help_text="Jr, Sr, I, II, III"
    )
    birthdate = models.DateField()
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)

    # Enrollment eligibility for Grade 1
    credential_presented = models.CharField(
        max_length=20, choices=CREDENTIAL_CHOICES, blank=True, null=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    other_credential = models.CharField(max_length=200, blank=True)
    pept_rating = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    pept_date = models.DateField(blank=True, null=True)
    pept_testing_center = models.CharField(max_length=200, blank=True)

    # Address Information
    country = models.CharField(max_length=50, default="Philippines")
    region = models.CharField(max_length=50, blank=True)
    province = models.CharField(max_length=100, blank=True)
    city = models.CharField(
        max_length=100, blank=True, verbose_name="City/Municipality"
    )
    barangay = models.CharField(max_length=100, blank=True)
    address_line1 = models.CharField(
        max_length=200, blank=True, verbose_name="House No./Street"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "Student"
        verbose_name_plural = "Students"

    def __str__(self):
        return f"{self.lrn} - {self.get_full_name()}"

    def get_full_name(self):
        """Return formatted full name"""
        name_parts = [self.first_name, self.middle_name, self.last_name]
        full_name = " ".join(filter(None, name_parts))
        if self.name_extension:
            full_name += f" {self.name_extension}"
        return full_name


class School(models.Model):
    """School information"""

    school_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    address = models.TextField()
    district = models.CharField(max_length=100)
    division = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    logo = models.ImageField(upload_to="school_logos/", blank=True, null=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "School"
        verbose_name_plural = "Schools"

    def __str__(self):
        return f"{self.name} ({self.school_id})"


class AcademicYear(models.Model):
    """Academic/School Year configuration"""

    year_label = models.CharField(
        max_length=9, unique=True, help_text="Format: 2024-2025"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(
        default=False, help_text="Mark this as the current active academic year"
    )

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Academic Year"
        verbose_name_plural = "Academic Years"

    def __str__(self):
        current_marker = " (Current)" if self.is_current else ""
        return f"{self.year_label}{current_marker}"

    @classmethod
    def get_current_year(cls):
        """Get the current active academic year"""
        current = cls.objects.filter(is_current=True).first()
        if not current:
            # Fallback to most recent year
            current = cls.objects.first()
        return current

    def save(self, *args, **kwargs):
        # Ensure only one year is marked as current
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class Section(models.Model):
    """Grade level sections managed by Registrar"""

    GRADE_CHOICES = [
        (7, "Grade 7"),
        (8, "Grade 8"),
        (9, "Grade 9"),
        (10, "Grade 10"),
    ]

    grade_level = models.IntegerField(choices=GRADE_CHOICES)
    name = models.CharField(max_length=50)
    max_students = models.IntegerField(
        default=45,
        null=True,
        blank=True,
        help_text="Maximum number of students allowed in this section",
    )

    class Meta:
        ordering = ["grade_level", "name"]
        unique_together = ["grade_level", "name"]
        verbose_name = "Section"
        verbose_name_plural = "Sections"

    def __str__(self):
        return f"Grade {self.grade_level} - {self.name}"

    def get_current_enrollment_count(self):
        """Get the current number of students enrolled in this section"""
        return (
            AcademicRecord.objects.filter(section=self, grade_level=self.grade_level)
            .exclude(remarks="PROMOTED")
            .values("student")
            .distinct()
            .count()
        )

    def get_available_slots(self):
        """Get the number of available slots remaining"""
        if self.max_students is None:
            return None  # Unlimited
        return max(0, self.max_students - self.get_current_enrollment_count())

    def is_full(self):
        """Check if the section is at capacity"""
        if self.max_students is None:
            return False  # Unlimited capacity
        return self.get_current_enrollment_count() >= self.max_students

    def is_near_capacity(self, threshold=0.9):
        """Check if section is near capacity (default 90%)"""
        if self.max_students is None:
            return False
        return self.get_current_enrollment_count() >= (self.max_students * threshold)


class TeacherProfile(models.Model):
    """Advisory information for Teachers"""

    user = models.OneToOneField(
        "auth.User", on_delete=models.CASCADE, related_name="teacher_profile"
    )
    grade_level = models.IntegerField(choices=Section.GRADE_CHOICES)
    section = models.ForeignKey(
        Section, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Teacher Profile"
        verbose_name_plural = "Teacher Profiles"

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.section if self.section else 'No Section'}"


class AcademicRecord(models.Model):
    """Academic record for a student in a specific grade level and school year"""

    GRADE_CHOICES = [
        (7, "Grade 7"),
        (8, "Grade 8"),
        (9, "Grade 9"),
        (10, "Grade 10"),
    ]

    REMARKS_CHOICES = [
        ("PASSED", "Passed"),
        ("FAILED", "Failed"),
        ("PROMOTED", "Promoted"),
        ("RETAINED", "Retained"),
    ]

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="academic_records"
    )
    school = models.ForeignKey(
        School, on_delete=models.PROTECT, related_name="academic_records"
    )
    grade_level = models.IntegerField(choices=GRADE_CHOICES)
    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="academic_records",
        null=True,
        blank=True,
    )
    school_year = models.CharField(max_length=9, help_text="Format: 2024-2025")
    adviser_teacher = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="advised_records",
    )

    # Computed fields
    general_average = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    remarks = models.CharField(max_length=20, choices=REMARKS_CHOICES, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-school_year", "grade_level"]
        unique_together = ["student", "grade_level", "school_year"]
        verbose_name = "Academic Record"
        verbose_name_plural = "Academic Records"
        indexes = [
            models.Index(fields=["student", "school_year"]),
            models.Index(fields=["grade_level", "school_year"]),
        ]

    def __str__(self):
        return f"{self.student.lrn} - Grade {self.grade_level} ({self.school_year})"

    def calculate_general_average(self):
        """
        Calculate general average based on final ratings of all subjects
        Follows DepEd Order No. 10, s. 2024
        """
        subject_grades = self.subject_grades.filter(final_rating__isnull=False)

        if not subject_grades.exists():
            return None

        total = sum(grade.get_final_rating() for grade in subject_grades)
        count = subject_grades.count()

        if count == 0:
            return None

        general_avg = Decimal(total) / Decimal(count)
        return round(general_avg, 2)

    def determine_remarks(self):
        """
        Determine pass/fail status based on DepEd 2025 standards
        - Grade 1-3: No failing grades (all subjects must be passed)
        - Grade 4-10: General average >= 75, no grade below 60
        """
        subject_grades = self.subject_grades.filter(final_rating__isnull=False)

        if not subject_grades.exists():
            return ""

        general_avg = self.calculate_general_average()

        if general_avg is None:
            return ""

        # Check for failing grades (below 75)
        failing_grades = subject_grades.filter(
            models.Q(final_rating__lt=75) | models.Q(final_rating__isnull=True)
        ).count()

        # Check for grades below 60 (automatic failure)
        critical_failing = subject_grades.filter(final_rating__lt=60).exists()

        # Grading standards
        if self.grade_level <= 3:
            # Grades 1-3: More lenient, focus on progress
            if failing_grades == 0:
                return "PROMOTED"
            else:
                return "RETAINED"
        else:
            # Grades 4-10: Standard grading
            if general_avg >= 75 and failing_grades == 0:
                # User requirement: All subjects passed -> PROMOTED
                return "PROMOTED"
            elif general_avg >= 75 and failing_grades <= 2 and not critical_failing:
                # Still allow PASSED if some subjects need remedial
                return "PASSED"
            else:
                return "FAILED"

    def update_computed_fields(self):
        """Update general average and remarks"""
        self.general_average = self.calculate_general_average()
        # Only auto-determine if not already manually set to PROMOTED/RETAINED
        if self.remarks not in ["PROMOTED", "RETAINED"]:
            self.remarks = self.determine_remarks()
        self.save(update_fields=["general_average", "remarks", "updated_at"])

    def retain(self):
        """Logic to manual retain student in current grade"""
        self.remarks = "RETAINED"
        self.save(update_fields=["remarks"])

    def get_subjects_for_remedial(self):
        """Return subjects that need remedial classes (final rating < 75 OR needs_remedial flag set)"""
        return self.subject_grades.filter(
            models.Q(needs_remedial=True) | models.Q(final_rating__lt=75)
        ).distinct()

    def promote(self):
        """Logic to promote student to the next grade level"""
        if self.grade_level >= 10:
            return None  # Cannot promote higher than Grade 10 here (graduation handled by signal)

        next_grade = self.grade_level + 1

        # Calculate next school year
        try:
            start_year, end_year = map(int, self.school_year.split("-"))
            next_school_year = f"{start_year + 1}-{end_year + 1}"
        except ValueError:
            # Fallback if format is invalid, keep current (user can edit)
            next_school_year = self.school_year

        # Check if record already exists
        existing = AcademicRecord.objects.filter(
            student=self.student,
            grade_level=next_grade,
            school_year=next_school_year,
        ).first()

        if existing:
            return existing

        return AcademicRecord.objects.create(
            student=self.student,
            school=self.school,
            grade_level=next_grade,
            section=None,  # Reset section for new grade level - Registrar will assign
            school_year=next_school_year,
            adviser_teacher=None,  # Clear adviser for new grade
        )


class LearningArea(models.Model):
    """
    Learning Areas based on MATATAG Curriculum
    Different subjects for different grade levels
    """

    GRADE_LEVEL_CHOICES = [
        ("7", "Grade 7"),
        ("8", "Grade 8"),
        ("9", "Grade 9"),
        ("10", "Grade 10"),
        ("ALL", "All Grades"),
    ]

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    applicable_grades = models.CharField(max_length=10, choices=GRADE_LEVEL_CHOICES)
    is_core = models.BooleanField(default=True)
    is_optional = models.BooleanField(
        default=False, help_text="e.g., Arabic Language, Islamic Values"
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Learning Area"
        verbose_name_plural = "Learning Areas"
        unique_together = ["code", "applicable_grades"]

    def __str__(self):
        return f"{self.name} ({self.applicable_grades})"

    @classmethod
    def get_subjects_for_grade(cls, grade_level):
        """Get applicable subjects for a specific grade level"""
        # Convert grade_level to string for comparison
        grade_str = str(grade_level)

        return cls.objects.filter(
            models.Q(applicable_grades=grade_str) | models.Q(applicable_grades="ALL")
        ).filter(is_core=True)


class SubjectGrade(models.Model):
    """Quarterly and final ratings for each subject"""

    academic_record = models.ForeignKey(
        AcademicRecord, on_delete=models.CASCADE, related_name="subject_grades"
    )
    learning_area = models.ForeignKey(
        LearningArea, on_delete=models.PROTECT, related_name="grades"
    )

    # Quarterly ratings (1-4 quarters)
    quarter_1 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    quarter_2 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    quarter_3 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    quarter_4 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # Final rating (average of quarters)
    final_rating = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # Remedial class information
    needs_remedial = models.BooleanField(default=False)
    remedial_conducted_from = models.DateField(blank=True, null=True)
    remedial_conducted_to = models.DateField(blank=True, null=True)
    remedial_mark = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    recomputed_final_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    remarks = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["learning_area__order", "learning_area__name"]
        unique_together = ["academic_record", "learning_area"]
        verbose_name = "Subject Grade"
        verbose_name_plural = "Subject Grades"
        indexes = [
            models.Index(fields=["academic_record", "learning_area"]),
        ]

    def __str__(self):
        return f"{self.academic_record.student.lrn} - {self.learning_area.name}"

    def calculate_final_rating(self):
        """Calculate final rating as average of quarterly ratings"""
        quarters = [self.quarter_1, self.quarter_2, self.quarter_3, self.quarter_4]
        valid_quarters = [q for q in quarters if q is not None]

        if not valid_quarters:
            return None

        avg = sum(valid_quarters) / len(valid_quarters)
        return round(Decimal(avg), 2)

    def get_final_rating(self):
        """Return final rating, or recomputed if available"""
        if self.recomputed_final_grade:
            return self.recomputed_final_grade
        return self.final_rating

    def update_final_rating(self):
        """Calculate and save final rating"""
        self.final_rating = self.calculate_final_rating()

        # Determine if remedial is needed
        if self.final_rating and self.final_rating < 75:
            self.needs_remedial = True
        elif (
            self.final_rating
            and self.final_rating >= 75
            and not self.recomputed_final_grade
        ):
            self.needs_remedial = False

        # Auto-generate remarks
        if self.final_rating:
            # Check recomputed grade first if it exists
            final_to_check = self.get_final_rating()
            if final_to_check >= 75:
                self.remarks = "Passed"
            else:
                self.remarks = "Failed"

        self.save(
            update_fields=["final_rating", "needs_remedial", "remarks", "updated_at"]
        )

    def clean(self):
        """Validation for remedial fields"""
        if self.needs_remedial:
            if self.remedial_mark and not (
                self.remedial_conducted_from and self.remedial_conducted_to
            ):
                raise ValidationError(
                    "Remedial dates must be provided if remedial mark is entered"
                )

        if self.remedial_mark and self.final_rating:
            # Recompute final grade (average of original and remedial)
            self.recomputed_final_grade = round(
                (self.final_rating + self.remedial_mark) / 2, 2
            )

    def save(self, *args, **kwargs):
        # Calculate final rating before saving
        self.final_rating = self.calculate_final_rating()

        # Determine if remedial is needed
        if self.final_rating and self.final_rating < 75:
            self.needs_remedial = True
        elif (
            self.final_rating
            and self.final_rating >= 75
            and not self.recomputed_final_grade
        ):
            self.needs_remedial = False

        # Auto-generate remarks
        if self.final_rating:
            # Check recomputed grade first if it exists
            final_to_check = self.get_final_rating()
            if final_to_check >= 75:
                self.remarks = "Passed"
            else:
                self.remarks = "Failed"

        self.clean()
        super().save(*args, **kwargs)

        # Update parent academic record
        if self.academic_record_id:
            self.academic_record.update_computed_fields()


# Signals


@receiver([post_save, post_delete], sender=SubjectGrade)
def update_academic_record_on_grade_change(sender, instance, **kwargs):
    """Automatically update academic record when grades change"""
    if instance.academic_record_id:
        instance.academic_record.update_computed_fields()


@receiver(post_save, sender=AcademicRecord)
def update_student_status_on_academic_change(sender, instance, created, **kwargs):
    """
    Update student status based on academic records.
    Also auto-populate subjects when a new record is created.
    """
    # 1. Auto-Populate Subjects for New Records
    if created:
        # Get subjects for this grade level
        subjects = LearningArea.get_subjects_for_grade(instance.grade_level)

        # Create Grade entries
        SubjectGrade.objects.bulk_create(
            [
                SubjectGrade(academic_record=instance, learning_area=subject)
                for subject in subjects
            ]
        )

    # 2. Update Student Status Logic (Existing)
    student = instance.student

    # Handle Initial Enrollment
    if created and student.status == "PENDING":
        student.status = "ENROLLED"
        student.save(update_fields=["status"])

    # Handle Graduation
    if instance.grade_level == 10 and instance.remarks == "PROMOTED":
        if student.status != "GRADUATED":
            student.status = "GRADUATED"
            student.save(update_fields=["status"])
