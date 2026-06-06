from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class User(AbstractUser):
    """System account shared by admins, tutors, and students.

    `role` is the long-term source of truth. The older boolean fields remain
    for compatibility with the existing code and are synchronized on save.
    """

    ROLE_ADMIN = "admin"
    ROLE_TUTOR = "tutor"
    ROLE_STUDENT = "student"
    ROLE_CHOICES = (
        (ROLE_ADMIN, "Admin"),
        (ROLE_TUTOR, "Tutor"),
        (ROLE_STUDENT, "Student"),
    )

    fullname = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    phone_number = models.CharField(max_length=30, blank=True)
    is_suspended = models.BooleanField(default=False)
    is_tutor = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)
    
    # Student specific (Null for tutors)
    school_name = models.CharField(max_length=255, blank=True, null=True)
    registration_id = models.CharField(max_length=100, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'fullname']

    @property
    def is_platform_admin(self):
        """Return True for users allowed into the platform admin dashboard."""
        return self.role == self.ROLE_ADMIN or self.is_staff or self.is_superuser

    def save(self, *args, **kwargs):
        """Keep legacy role booleans aligned while the model evolves."""
        if self.is_staff or self.is_superuser:
            self.role = self.ROLE_ADMIN
        self.is_tutor = self.role == self.ROLE_TUTOR
        self.is_student = self.role == self.ROLE_STUDENT
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fullname} ({self.get_role_display()})"


class TutorProfile(models.Model):
    """Tutor-specific business profile used for billing and school context."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="tutor_profile")
    institution_name = models.CharField(max_length=255, blank=True)
    county = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Tutor profile for {self.user.fullname}"


class StudentProfile(models.Model):
    """Student identity provisioned by a tutor or admin.

    The registration number is scoped to the tutor because different schools
    can reuse similar admission numbers.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="provisioned_students")
    school_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100)
    must_change_password = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tutor", "registration_number"],
                name="unique_student_registration_per_tutor",
            )
        ]

    def __str__(self):
        return f"{self.user.fullname} ({self.registration_number})"

# 2. Classroom Model
class Classroom(models.Model):
    """Tutor-owned learning group used to assign students and assessments."""

    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_rooms')
    name = models.CharField(max_length=255)
    room_id = models.CharField(max_length=50, unique=True) # The unique ID for joining
    password = models.CharField(max_length=50, blank=True) # Legacy field; do not expose publicly.
    students = models.ManyToManyField(User, related_name='joined_rooms', blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# 3. Exam Model
class Exam(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='exams')
    title = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True) # Null = no end time
    
    # Exam Configurations
    attempts_allowed = models.PositiveIntegerField(default=1)
    back_btn_enabled = models.BooleanField(default=True)
    show_results_immediately = models.BooleanField(default=True)
    show_answers = models.BooleanField(default=True) # If student can see what was correct
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

# 4. Question & Choice Models
class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    # We store the labels like "A, D" as a string to match your Excel logic
    correct_labels = models.CharField(max_length=100, help_text="e.g., A or A,D") 
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.exam.title} - Q{self.order}"

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    label = models.CharField(max_length=10) # A, B, C, D...
    text = models.TextField()

    def __str__(self):
        return f"{self.label}: {self.text}"

# 5. Results & Monitoring Models
class Submission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    completed = models.BooleanField(default=False)
    attempt_number = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(auto_now_add=True)

class StudentAnswer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choices = models.CharField(max_length=100) # Stores "A,C" etc.

class ProctorLog(models.Model):
    VIOLATION_TYPES = (
        ('TAB_SWITCH', 'Left Page/Tab'),
        ('COPY_PASTE', 'Attempted Copy/Paste'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    violation_type = models.CharField(max_length=50, choices=VIOLATION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)

class SiteStatistic(models.Model):
    """
    Model to store and manually override site-wide impact stats 
    if auto-counting isn't preferred.
    """
    tutor_count = models.PositiveIntegerField(default=0)
    student_count = models.PositiveIntegerField(default=0)
    classroom_count = models.PositiveIntegerField(default=0)
    exam_count = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Site Statistics"

    def __str__(self):
        return f"Stats updated on {self.last_updated.strftime('%Y-%m-%d')}"

class ContactMessage(models.Model):
    """
    Stores messages sent via the contact form on the index page.
    """
    name = models.CharField(max_length=255)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.name} - {self.created_at.date()}"
