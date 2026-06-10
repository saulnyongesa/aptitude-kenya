from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
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
    """Tutor-created assessment assigned to one classroom.

    The historical model name remains `Exam`, but `assessment_type` now lets
    the platform represent quizzes, tests, CATs, assignments, and exams.
    """

    TYPE_QUIZ = "quiz"
    TYPE_ASSIGNMENT = "assignment"
    TYPE_TEST = "test"
    TYPE_CAT = "cat"
    TYPE_EXAM = "exam"
    ASSESSMENT_TYPE_CHOICES = (
        (TYPE_QUIZ, "Quiz"),
        (TYPE_ASSIGNMENT, "Assignment"),
        (TYPE_TEST, "Test"),
        (TYPE_CAT, "CAT"),
        (TYPE_EXAM, "Exam"),
    )

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_ARCHIVED, "Archived"),
    )

    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='exams')
    title = models.CharField(max_length=255)
    assessment_type = models.CharField(max_length=30, choices=ASSESSMENT_TYPE_CHOICES, default=TYPE_TEST)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    instructions = models.TextField(blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True) # Null = no end time
    duration_minutes = models.PositiveIntegerField(default=60)
    total_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    pass_mark = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Exam Configurations
    attempts_allowed = models.PositiveIntegerField(default=1)
    back_btn_enabled = models.BooleanField(default=True)
    allow_late_submission = models.BooleanField(default=False)
    show_results_immediately = models.BooleanField(default=True)
    show_answers = models.BooleanField(default=True) # If student can see what was correct
    randomize_questions = models.BooleanField(default=False)
    randomize_choices = models.BooleanField(default=False)
    proctoring_enabled = models.BooleanField(default=False)
    disable_copy_paste = models.BooleanField(default=False)
    disable_right_click = models.BooleanField(default=False)
    disable_text_selection = models.BooleanField(default=False)
    detect_tab_switch = models.BooleanField(default=False)
    detect_window_blur = models.BooleanField(default=False)
    require_fullscreen = models.BooleanField(default=False)
    detect_fullscreen_exit = models.BooleanField(default=False)
    detect_refresh = models.BooleanField(default=False)
    max_violation_warnings = models.PositiveIntegerField(default=3)
    auto_submit_on_violation = models.BooleanField(default=False)
    auto_disqualify_on_violation = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class QuestionSection(models.Model):
    """Ordered section within an assessment."""

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.exam.title} - {self.title}"

# 4. Question & Choice Models
class Question(models.Model):
    """Assessment question with rich text and optional media attachment URL."""

    TYPE_SINGLE_CHOICE = "single_choice"
    TYPE_MULTIPLE_CHOICE = "multiple_choice"
    TYPE_TRUE_FALSE = "true_false"
    TYPE_SHORT_ANSWER = "short_answer"
    TYPE_ESSAY = "essay"
    TYPE_FILE_UPLOAD = "file_upload"
    TYPE_PASSAGE = "passage"
    QUESTION_TYPE_CHOICES = (
        (TYPE_SINGLE_CHOICE, "Single choice"),
        (TYPE_MULTIPLE_CHOICE, "Multiple choice"),
        (TYPE_TRUE_FALSE, "True/false"),
        (TYPE_SHORT_ANSWER, "Short answer"),
        (TYPE_ESSAY, "Essay"),
        (TYPE_FILE_UPLOAD, "File upload"),
        (TYPE_PASSAGE, "Passage based"),
    )

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    section = models.ForeignKey(QuestionSection, on_delete=models.SET_NULL, related_name='questions', blank=True, null=True)
    question_type = models.CharField(max_length=30, choices=QUESTION_TYPE_CHOICES, default=TYPE_SINGLE_CHOICE)
    text = models.TextField()
    explanation = models.TextField(blank=True)
    media_url = models.URLField(blank=True)
    marks = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    # We store the labels like "A, D" as a string to match your Excel logic
    correct_labels = models.CharField(max_length=100, blank=True, help_text="e.g., A or A,D") 
    order = models.PositiveIntegerField(default=0)
    reusable_in_bank = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.exam.title} - Q{self.order}"

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    label = models.CharField(max_length=10) # A, B, C, D...
    text = models.TextField()

    def __str__(self):
        return f"{self.label}: {self.text}"


class QuestionBankItem(models.Model):
    """Reusable tutor-owned question template copied into assessments."""

    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='question_bank_items')
    title = models.CharField(max_length=255)
    question_type = models.CharField(max_length=30, choices=Question.QUESTION_TYPE_CHOICES, default=Question.TYPE_SINGLE_CHOICE)
    text = models.TextField()
    explanation = models.TextField(blank=True)
    media_url = models.URLField(blank=True)
    marks = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    correct_labels = models.CharField(max_length=100, blank=True)
    choices_json = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class PlatformPricing(models.Model):
    """Admin-owned default pricing for pay-per-assessment billing."""

    currency = models.CharField(max_length=10, default="KES")
    pay_per_student_rate = models.DecimalField(max_digits=10, decimal_places=2, default=5)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Platform Pricing"

    def __str__(self):
        return f"{self.currency} {self.pay_per_student_rate} per student"


class SubscriptionPlan(models.Model):
    """Tutor subscription option configured by the platform admin."""

    ANTI_CHEATING_NONE = "none"
    ANTI_CHEATING_STANDARD = "standard"
    ANTI_CHEATING_STRICT = "strict"
    ANTI_CHEATING_CHOICES = (
        (ANTI_CHEATING_NONE, "No anti-cheating"),
        (ANTI_CHEATING_STANDARD, "Standard anti-cheating"),
        (ANTI_CHEATING_STRICT, "Strict anti-cheating"),
    )

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    duration_months = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="KES")
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    anti_cheating_level = models.CharField(
        max_length=20,
        choices=ANTI_CHEATING_CHOICES,
        default=ANTI_CHEATING_STANDARD,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price", "duration_months", "name"]

    def __str__(self):
        return f"{self.name} ({self.duration_months} months)"


class Invoice(models.Model):
    """Amount owed by a tutor for one assessment or subscription plan."""

    TYPE_ASSESSMENT = "assessment"
    TYPE_SUBSCRIPTION = "subscription"
    TYPE_CHOICES = (
        (TYPE_ASSESSMENT, "Assessment"),
        (TYPE_SUBSCRIPTION, "Subscription"),
    )

    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invoices")
    assessment = models.ForeignKey(Exam, on_delete=models.SET_NULL, related_name="invoices", null=True, blank=True)
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        related_name="invoices",
        null=True,
        blank=True,
    )
    invoice_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reference = models.CharField(max_length=40, unique=True, blank=True)
    currency = models.CharField(max_length=10, default="KES")
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"AK-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} - {self.get_invoice_type_display()}"


class Payment(models.Model):
    """Payment attempt against an invoice."""

    METHOD_MPESA = "mpesa"
    METHOD_MANUAL = "manual"
    METHOD_CHOICES = (
        (METHOD_MPESA, "M-Pesa"),
        (METHOD_MANUAL, "Manual"),
    )

    STATUS_PENDING = "pending"
    STATUS_SUCCESSFUL = "successful"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESSFUL, "Successful"),
        (STATUS_FAILED, "Failed"),
    )

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="KES")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_MPESA)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    provider_reference = models.CharField(max_length=120, blank=True)
    merchant_request_id = models.CharField(max_length=120, blank=True)
    checkout_request_id = models.CharField(max_length=120, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.invoice.reference} - {self.get_status_display()}"


class TutorSubscription(models.Model):
    """Active or historical tutor subscription period."""

    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    invoice = models.OneToOneField(Invoice, on_delete=models.SET_NULL, related_name="subscription", null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_active_now(self):
        if not self.starts_at or not self.ends_at:
            return False
        now = timezone.now()
        return self.status == self.STATUS_ACTIVE and self.starts_at <= now <= self.ends_at

    def __str__(self):
        return f"{self.tutor.email} - {self.plan.name}"


class MpesaTransaction(models.Model):
    """Raw M-Pesa callback record used for idempotent reconciliation."""

    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, related_name="mpesa_transactions", null=True, blank=True)
    merchant_request_id = models.CharField(max_length=120, blank=True)
    checkout_request_id = models.CharField(max_length=120, blank=True, db_index=True)
    receipt_number = models.CharField(max_length=120, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    result_code = models.IntegerField(null=True, blank=True)
    result_description = models.TextField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    callback_received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-callback_received_at"]

    def __str__(self):
        return self.receipt_number or self.checkout_request_id or "M-Pesa callback"

# 5. Results & Monitoring Models
class Submission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    completed = models.BooleanField(default=False)
    is_disqualified = models.BooleanField(default=False)
    disqualified_at = models.DateTimeField(null=True, blank=True)
    disqualification_reason = models.TextField(blank=True)
    attempt_number = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True, null=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_saved_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.student.email} - {self.exam.title} attempt {self.attempt_number}"

class StudentAnswer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choices = models.TextField(blank=True) # Stores labels, short text, or written responses.
    awarded_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_correct = models.BooleanField(default=False)
    saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "question"],
                name="unique_answer_per_submission_question",
            )
        ]

    def __str__(self):
        return f"{self.submission} - Q{self.question_id}"


class StudentTodo(models.Model):
    """Student-owned task shown on the dashboard alongside assessments."""

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="todos")
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    assessment = models.ForeignKey(Exam, on_delete=models.SET_NULL, related_name="student_todos", null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_completed", "due_at", "-created_at"]

    def mark_complete(self):
        self.is_completed = True
        self.completed_at = timezone.now()
        self.save(update_fields=["is_completed", "completed_at"])

    def __str__(self):
        return self.title


class StudentReminder(models.Model):
    """Reminder scheduled for a student assessment or manual task."""

    KIND_ASSESSMENT_START = "assessment_start"
    KIND_ASSESSMENT_DUE = "assessment_due"
    KIND_TODO = "todo"
    KIND_CHOICES = (
        (KIND_ASSESSMENT_START, "Assessment start"),
        (KIND_ASSESSMENT_DUE, "Assessment due"),
        (KIND_TODO, "Todo"),
    )

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reminders")
    assessment = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="student_reminders", null=True, blank=True)
    todo = models.ForeignKey(StudentTodo, on_delete=models.CASCADE, related_name="reminders", null=True, blank=True)
    title = models.CharField(max_length=255)
    remind_at = models.DateTimeField()
    kind = models.CharField(max_length=30, choices=KIND_CHOICES, default=KIND_ASSESSMENT_DUE)
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_sent", "remind_at"]

    def __str__(self):
        return self.title


class StudentNotification(models.Model):
    """In-app notification for student dashboard updates."""

    TYPE_ASSESSMENT = "assessment"
    TYPE_REMINDER = "reminder"
    TYPE_RESULT = "result"
    TYPE_SYSTEM = "system"
    TYPE_CHOICES = (
        (TYPE_ASSESSMENT, "Assessment"),
        (TYPE_REMINDER, "Reminder"),
        (TYPE_RESULT, "Result"),
        (TYPE_SYSTEM, "System"),
    )

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    assessment = models.ForeignKey(Exam, on_delete=models.SET_NULL, related_name="student_notifications", null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default=TYPE_SYSTEM)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["is_read", "-created_at"]

    def mark_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=["is_read", "read_at"])

    def __str__(self):
        return self.title

class ProctorLog(models.Model):
    """Evidence log for student proctoring events during an attempt."""

    TYPE_TAB_SWITCH = "TAB_SWITCH"
    TYPE_WINDOW_BLUR = "WINDOW_BLUR"
    TYPE_COPY = "COPY"
    TYPE_PASTE = "PASTE"
    TYPE_CONTEXT_MENU = "CONTEXT_MENU"
    TYPE_TEXT_SELECTION = "TEXT_SELECTION"
    TYPE_FULLSCREEN_EXIT = "FULLSCREEN_EXIT"
    TYPE_REFRESH = "REFRESH"
    TYPE_MULTIPLE_SESSION = "MULTIPLE_SESSION"
    VIOLATION_TYPES = (
        (TYPE_TAB_SWITCH, 'Left Page/Tab'),
        (TYPE_WINDOW_BLUR, 'Window Lost Focus'),
        (TYPE_COPY, 'Attempted Copy'),
        (TYPE_PASTE, 'Attempted Paste'),
        (TYPE_CONTEXT_MENU, 'Attempted Right Click'),
        (TYPE_TEXT_SELECTION, 'Attempted Text Selection'),
        (TYPE_FULLSCREEN_EXIT, 'Exited Fullscreen'),
        (TYPE_REFRESH, 'Refresh/Reload Attempt'),
        (TYPE_MULTIPLE_SESSION, 'Possible Multiple Session'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="proctor_logs", null=True, blank=True)
    violation_type = models.CharField(max_length=50, choices=VIOLATION_TYPES)
    details = models.TextField(blank=True)
    violation_count = models.PositiveIntegerField(default=1)
    triggered_disqualification = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.student.email} - {self.violation_type}"

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


class PlatformAnnouncement(models.Model):
    """Admin-authored notice shown to tutors, students, or everyone."""

    AUDIENCE_ALL = "all"
    AUDIENCE_TUTORS = "tutors"
    AUDIENCE_STUDENTS = "students"
    AUDIENCE_CHOICES = (
        (AUDIENCE_ALL, "All users"),
        (AUDIENCE_TUTORS, "Tutors"),
        (AUDIENCE_STUDENTS, "Students"),
    )

    title = models.CharField(max_length=255)
    message = models.TextField()
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL)
    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="created_announcements", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class SupportIssue(models.Model):
    """Admin-tracked support item raised from contact messages or manually."""

    STATUS_OPEN = "open"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_RESOLVED = "resolved"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = (
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CLOSED, "Closed"),
    )

    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_CHOICES = (
        (PRIORITY_LOW, "Low"),
        (PRIORITY_NORMAL, "Normal"),
        (PRIORITY_HIGH, "High"),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="support_issues", null=True, blank=True)
    contact_message = models.ForeignKey(ContactMessage, on_delete=models.SET_NULL, related_name="support_issues", null=True, blank=True)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_OPEN)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="assigned_support_issues", null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "-updated_at"]

    def __str__(self):
        return self.subject


class AuditLog(models.Model):
    """Append-only admin action log for operational accountability."""

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, related_name="audit_logs", null=True, blank=True)
    action = models.CharField(max_length=120)
    target_model = models.CharField(max_length=120, blank=True)
    target_id = models.CharField(max_length=120, blank=True)
    summary = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} by {self.actor}"


class BackgroundTaskLog(models.Model):
    """Persistent record for threaded or Celery background work."""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    )

    BACKEND_THREADING = "threading"
    BACKEND_CELERY = "celery"
    BACKEND_INLINE = "inline"
    BACKEND_CHOICES = (
        (BACKEND_THREADING, "Threading"),
        (BACKEND_CELERY, "Celery"),
        (BACKEND_INLINE, "Inline"),
    )

    task_name = models.CharField(max_length=160)
    backend = models.CharField(max_length=30, choices=BACKEND_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    args = models.JSONField(default=list, blank=True)
    kwargs = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task_name} - {self.status}"
