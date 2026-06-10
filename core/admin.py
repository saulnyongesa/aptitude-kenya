from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AuditLog, BackgroundTaskLog, User, TutorProfile, StudentProfile, Classroom, Exam, QuestionSection, Question, Choice, QuestionBankItem, PlatformPricing, SubscriptionPlan, Invoice, Payment, TutorSubscription, MpesaTransaction, Submission, StudentAnswer, StudentTodo, StudentReminder, StudentNotification, ProctorLog, SiteStatistic, ContactMessage, PlatformAnnouncement, SupportIssue

# --- 1. Custom User Admin ---
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'fullname', 'role', 'phone_number', 'is_suspended', 'is_staff')
    list_filter = ('role', 'is_suspended', 'is_staff')
    search_fields = ('email', 'fullname', 'registration_id')
    ordering = ('email',)
    
    # Organizes the detail view in the admin
    fieldsets = UserAdmin.fieldsets + (
        ('Aptitude Kenya Role', {'fields': ('role', 'phone_number', 'is_suspended')}),
        ('Legacy Student Info', {'fields': ('school_name', 'registration_id')}),
    )

@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution_name', 'county', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'county')
    search_fields = ('user__email', 'user__fullname', 'institution_name')

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tutor', 'school_name', 'registration_number', 'must_change_password')
    list_filter = ('school_name', 'must_change_password')
    search_fields = ('user__email', 'user__fullname', 'registration_number', 'tutor__email')

# --- 2. Classroom Admin ---
@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_id', 'tutor', 'is_archived', 'created_at')
    search_fields = ('name', 'room_id', 'tutor__email')
    list_filter = ('is_archived', 'created_at')
    filter_horizontal = ('students',) # Makes selecting students easier

# --- 3. Exam & Question Architecture ---
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4 # Default to 4 choices (A, B, C, D)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'exam', 'question_type', 'marks', 'correct_labels', 'order')
    list_filter = ('exam', 'question_type', 'reusable_in_bank')
    inlines = [ChoiceInline]

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'assessment_type', 'status', 'classroom', 'start_time', 'end_time', 'attempts_allowed', 'proctoring_enabled')
    list_filter = ('assessment_type', 'status', 'proctoring_enabled', 'auto_disqualify_on_violation', 'back_btn_enabled', 'show_results_immediately', 'classroom')
    search_fields = ('title', 'classroom__name')

@admin.register(QuestionSection)
class QuestionSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'exam', 'order')
    list_filter = ('exam',)

@admin.register(QuestionBankItem)
class QuestionBankItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'tutor', 'question_type', 'marks', 'created_at')
    list_filter = ('question_type', 'created_at')
    search_fields = ('title', 'text', 'tutor__email')


@admin.register(PlatformPricing)
class PlatformPricingAdmin(admin.ModelAdmin):
    list_display = ('currency', 'pay_per_student_rate', 'is_active', 'updated_at')
    list_filter = ('is_active',)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_months', 'price', 'currency', 'discount_percent', 'anti_cheating_level', 'is_active')
    list_filter = ('is_active', 'anti_cheating_level', 'duration_months')
    search_fields = ('name', 'description')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('reference', 'tutor', 'invoice_type', 'status', 'currency', 'total_amount', 'created_at', 'paid_at')
    list_filter = ('invoice_type', 'status', 'currency', 'created_at')
    search_fields = ('reference', 'tutor__email', 'assessment__title')
    readonly_fields = ('reference', 'created_at', 'paid_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'tutor', 'method', 'status', 'amount', 'provider_reference', 'created_at', 'confirmed_at')
    list_filter = ('method', 'status', 'created_at')
    search_fields = ('invoice__reference', 'tutor__email', 'provider_reference', 'checkout_request_id')


@admin.register(TutorSubscription)
class TutorSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('tutor', 'plan', 'status', 'starts_at', 'ends_at')
    list_filter = ('status', 'plan')
    search_fields = ('tutor__email', 'plan__name')


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ('receipt_number', 'checkout_request_id', 'result_code', 'amount', 'phone_number', 'callback_received_at')
    list_filter = ('result_code', 'callback_received_at')
    search_fields = ('receipt_number', 'checkout_request_id', 'merchant_request_id', 'phone_number')
    readonly_fields = ('raw_payload', 'callback_received_at')

# --- 4. Submissions & Monitoring ---
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'score', 'completed', 'is_disqualified', 'attempt_number', 'started_at', 'submitted_at')
    list_filter = ('completed', 'is_disqualified', 'exam')
    search_fields = ('student__fullname', 'student__email')
    readonly_fields = ('started_at', 'last_saved_at', 'submitted_at') # History shouldn't be tampered with

@admin.register(ProctorLog)
class ProctorLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'submission', 'violation_type', 'violation_count', 'triggered_disqualification', 'timestamp')
    list_filter = ('violation_type', 'triggered_disqualification', 'exam')
    search_fields = ('student__fullname', 'exam__title')
    # Logs are evidence; they should be read-only in a production environment
    readonly_fields = ('student', 'exam', 'submission', 'violation_type', 'details', 'violation_count', 'triggered_disqualification', 'timestamp')

# Registering the detail view for student answers
admin.site.register(StudentAnswer)


@admin.register(StudentTodo)
class StudentTodoAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'assessment', 'due_at', 'is_completed', 'created_at')
    list_filter = ('is_completed', 'due_at', 'created_at')
    search_fields = ('title', 'student__email', 'student__fullname', 'assessment__title')


@admin.register(StudentReminder)
class StudentReminderAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'kind', 'remind_at', 'is_sent', 'sent_at')
    list_filter = ('kind', 'is_sent', 'remind_at')
    search_fields = ('title', 'student__email', 'student__fullname', 'assessment__title')


@admin.register(StudentNotification)
class StudentNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'student__email', 'student__fullname', 'assessment__title')


@admin.register(SiteStatistic)
class SiteStatisticAdmin(admin.ModelAdmin):
    list_display = ('tutor_count', 'student_count', 'exam_count', 'last_updated')

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email')


@admin.register(PlatformAnnouncement)
class PlatformAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'audience', 'is_active', 'starts_at', 'ends_at', 'created_by', 'created_at')
    list_filter = ('audience', 'is_active', 'created_at')
    search_fields = ('title', 'message')


@admin.register(SupportIssue)
class SupportIssueAdmin(admin.ModelAdmin):
    list_display = ('subject', 'status', 'priority', 'user', 'assigned_to', 'updated_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('subject', 'description', 'user__email')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'actor', 'target_model', 'target_id', 'created_at')
    list_filter = ('action', 'target_model', 'created_at')
    search_fields = ('action', 'summary', 'actor__email')
    readonly_fields = ('actor', 'action', 'target_model', 'target_id', 'summary', 'metadata', 'created_at')


@admin.register(BackgroundTaskLog)
class BackgroundTaskLogAdmin(admin.ModelAdmin):
    list_display = ('task_name', 'backend', 'status', 'created_at', 'started_at', 'finished_at')
    list_filter = ('backend', 'status', 'task_name', 'created_at')
    search_fields = ('task_name', 'error_message')
    readonly_fields = ('task_name', 'backend', 'status', 'args', 'kwargs', 'result', 'error_message', 'created_at', 'started_at', 'finished_at')
