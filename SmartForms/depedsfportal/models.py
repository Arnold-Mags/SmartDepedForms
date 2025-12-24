from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class Student(models.Model):
    """Student master record with LRN as primary key"""
    SEX_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    CREDENTIAL_CHOICES = [
        ('KINDER_PROGRESS', 'Kinder Progress Report'),
        ('ECCD_CHECKLIST', 'ECCD Checklist'),
        ('KINDER_CERTIFICATE', 'Kindergarten Certificate of Completion'),
        ('PEPT', 'PEPT Passer'),
        ('OTHER', 'Other Credential'),
    ]
    
    lrn = models.CharField(
        max_length=12,
        primary_key=True,
        verbose_name="Learner Reference Number"
    )
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    name_extension = models.CharField(max_length=10, blank=True, help_text="Jr, Sr, I, II, III")
    birthdate = models.DateField()
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    
    # Enrollment eligibility for Grade 1
    credential_presented = models.CharField(
        max_length=20,
        choices=CREDENTIAL_CHOICES,
        blank=True,
        null=True
    )
    other_credential = models.CharField(max_length=200, blank=True)
    pept_rating = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    pept_date = models.DateField(blank=True, null=True)
    pept_testing_center = models.CharField(max_length=200, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = "Student"
        verbose_name_plural = "Students"
    
    def __str__(self):
        return f"{self.lrn} - {self.get_full_name()}"
    
    def get_full_name(self):
        """Return formatted full name"""
        name_parts = [self.first_name, self.middle_name, self.last_name]
        full_name = ' '.join(filter(None, name_parts))
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
    
    class Meta:
        ordering = ['name']
        verbose_name = "School"
        verbose_name_plural = "Schools"
    
    def __str__(self):
        return f"{self.name} ({self.school_id})"


class AcademicRecord(models.Model):
    """Academic record for a student in a specific grade level and school year"""
    GRADE_CHOICES = [
        (1, 'Grade 7'),
        (2, 'Grade 8'),
        (3, 'Grade 9'),
        (4, 'Grade 10'),
    ]
    
    REMARKS_CHOICES = [
        ('PASSED', 'Passed'),
        ('FAILED', 'Failed'),
        ('PROMOTED', 'Promoted'),
        ('RETAINED', 'Retained'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='academic_records'
    )
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name='academic_records'
    )
    grade_level = models.IntegerField(choices=GRADE_CHOICES)
    section = models.CharField(max_length=50)
    school_year = models.CharField(max_length=9, help_text="Format: 2024-2025")
    adviser_teacher = models.CharField(max_length=200)
    
    # Computed fields
    general_average = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    remarks = models.CharField(max_length=20, choices=REMARKS_CHOICES, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-school_year', 'grade_level']
        unique_together = ['student', 'grade_level', 'school_year']
        verbose_name = "Academic Record"
        verbose_name_plural = "Academic Records"
        indexes = [
            models.Index(fields=['student', 'school_year']),
            models.Index(fields=['grade_level', 'school_year']),
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
            return None
        
        general_avg = self.calculate_general_average()
        
        if general_avg is None:
            return None
        
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
                return 'PROMOTED'
            else:
                return 'RETAINED'
        else:
            # Grades 4-10: Standard grading
            if general_avg >= 75 and not critical_failing and failing_grades == 0:
                return 'PASSED'
            elif general_avg >= 75 and failing_grades <= 2 and not critical_failing:
                # Allow promotion with remedial for 1-2 subjects
                return 'PROMOTED'
            else:
                return 'FAILED'
    
    def update_computed_fields(self):
        """Update general average and remarks"""
        self.general_average = self.calculate_general_average()
        self.remarks = self.determine_remarks()
        self.save(update_fields=['general_average', 'remarks', 'updated_at'])
    
    def get_subjects_for_remedial(self):
        """Return subjects that need remedial classes (final rating < 75)"""
        return self.subject_grades.filter(
            final_rating__lt=75,
            final_rating__gte=60
        )


class LearningArea(models.Model):
    """
    Learning Areas based on MATATAG Curriculum
    Different subjects for different grade levels
    """
    GRADE_LEVEL_CHOICES = [
        ('1-3', 'Grades 1-3'),
        ('4-6', 'Grades 4-6'),
        ('7-10', 'Grades 7-10'),
        ('ALL', 'All Grades'),
    ]
    
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    applicable_grades = models.CharField(max_length=10, choices=GRADE_LEVEL_CHOICES)
    is_core = models.BooleanField(default=True)
    is_optional = models.BooleanField(default=False, help_text="e.g., Arabic Language, Islamic Values")
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Learning Area"
        verbose_name_plural = "Learning Areas"
    
    def __str__(self):
        return f"{self.name} ({self.applicable_grades})"
    
    @classmethod
    def get_subjects_for_grade(cls, grade_level):
        """Get applicable subjects for a specific grade level"""
        if 1 <= grade_level <= 3:
            grade_range = '1-3'
        elif 4 <= grade_level <= 6:
            grade_range = '4-6'
        elif 7 <= grade_level <= 10:
            grade_range = '7-10'
        else:
            return cls.objects.none()
        
        return cls.objects.filter(
            models.Q(applicable_grades=grade_range) | models.Q(applicable_grades='ALL')
        ).filter(is_core=True)


class SubjectGrade(models.Model):
    """Quarterly and final ratings for each subject"""
    academic_record = models.ForeignKey(
        AcademicRecord,
        on_delete=models.CASCADE,
        related_name='subject_grades'
    )
    learning_area = models.ForeignKey(
        LearningArea,
        on_delete=models.PROTECT,
        related_name='grades'
    )
    
    # Quarterly ratings (1-4 quarters)
    quarter_1 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    quarter_2 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    quarter_3 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    quarter_4 = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Final rating (average of quarters)
    final_rating = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
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
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    recomputed_final_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    remarks = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['learning_area__order', 'learning_area__name']
        unique_together = ['academic_record', 'learning_area']
        verbose_name = "Subject Grade"
        verbose_name_plural = "Subject Grades"
        indexes = [
            models.Index(fields=['academic_record', 'learning_area']),
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
        if self.final_rating and 60 <= self.final_rating < 75:
            self.needs_remedial = True
        else:
            self.needs_remedial = False
        
        # Auto-generate remarks
        if self.final_rating:
            if self.final_rating >= 75:
                self.remarks = "Passed"
            elif self.final_rating >= 60:
                self.remarks = "Needs Remedial"
            else:
                self.remarks = "Failed"
        
        self.save(update_fields=['final_rating', 'needs_remedial', 'remarks', 'updated_at'])
    
    def clean(self):
        """Validation for remedial fields"""
        if self.needs_remedial:
            if self.remedial_mark and not (self.remedial_conducted_from and self.remedial_conducted_to):
                raise ValidationError("Remedial dates must be provided if remedial mark is entered")
        
        if self.remedial_mark and self.final_rating:
            # Recompute final grade (average of original and remedial)
            self.recomputed_final_grade = round((self.final_rating + self.remedial_mark) / 2, 2)
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        # Update parent academic record
        if self.academic_record_id:
            self.academic_record.update_computed_fields()


# Signal to auto-update grades when subject grades change

@receiver([post_save, post_delete], sender=SubjectGrade)
def update_academic_record_on_grade_change(sender, instance, **kwargs):
    """Automatically update academic record when grades change"""
    if instance.academic_record_id:
        instance.academic_record.update_computed_fields()