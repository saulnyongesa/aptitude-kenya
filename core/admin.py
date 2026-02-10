from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Classroom, Exam, Question, Choice, Submission, StudentAnswer, ProctorLog, SiteStatistic, ContactMessage

# --- 1. Custom User Admin ---
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'fullname', 'is_tutor', 'is_student', 'school_name', 'registration_id')
    list_filter = ('is_tutor', 'is_student', 'school_name')
    search_fields = ('email', 'fullname', 'registration_id')
    ordering = ('email',)
    
    # Organizes the detail view in the admin
    fieldsets = UserAdmin.fieldsets + (
        ('Aptitude-Kenya Roles', {'fields': ('is_tutor', 'is_student')}),
        ('Student Info', {'fields': ('school_name', 'registration_id')}),
    )

# --- 2. Classroom Admin ---
@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_id', 'tutor', 'created_at')
    search_fields = ('name', 'room_id', 'tutor__email')
    list_filter = ('created_at',)
    filter_horizontal = ('students',) # Makes selecting students easier

# --- 3. Exam & Question Architecture ---
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4 # Default to 4 choices (A, B, C, D)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'exam', 'correct_labels', 'order')
    list_filter = ('exam',)
    inlines = [ChoiceInline]

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'classroom', 'start_time', 'end_time', 'attempts_allowed')
    list_filter = ('back_btn_enabled', 'show_results_immediately', 'classroom')
    search_fields = ('title', 'classroom__name')

# --- 4. Submissions & Monitoring ---
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'score', 'completed', 'attempt_number')
    list_filter = ('completed', 'exam')
    search_fields = ('student__fullname', 'student__email')
    readonly_fields = ('submitted_at',) # History shouldn't be tampered with

@admin.register(ProctorLog)
class ProctorLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'violation_type', 'timestamp')
    list_filter = ('violation_type', 'exam')
    search_fields = ('student__fullname', 'exam__title')
    # Logs are evidence; they should be read-only in a production environment
    readonly_fields = ('student', 'exam', 'violation_type', 'timestamp')

# Registering the detail view for student answers
admin.site.register(StudentAnswer)
@admin.register(SiteStatistic)
class SiteStatisticAdmin(admin.ModelAdmin):
    list_display = ('tutor_count', 'student_count', 'exam_count', 'last_updated')

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email')