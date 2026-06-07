from django import forms
from django.contrib.auth import authenticate

from .models import Classroom, Exam, Question, QuestionBankItem, QuestionSection, StudentProfile, User


class TutorRegistrationForm(forms.Form):
    """Validate public tutor self-registration details."""

    fullname = forms.CharField(max_length=255)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=30, required=False)
    institution_name = forms.CharField(max_length=255, required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned


class LoginForm(forms.Form):
    """Authenticate a user by password or student registration number."""

    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "").lower()
        password = cleaned.get("password", "")
        if not email or not password:
            return cleaned

        user = authenticate(username=email, password=password)
        if user is None:
            user = self._authenticate_student_registration(email, password)

        if user is None:
            raise forms.ValidationError("Invalid email or password.")
        if user.is_suspended:
            raise forms.ValidationError("This account has been suspended.")

        cleaned["user"] = user
        return cleaned

    def _authenticate_student_registration(self, email, registration_number):
        """Allow provisioned students to log in with school registration."""
        try:
            profile = StudentProfile.objects.select_related("user").get(
                user__email=email,
                registration_number=registration_number,
                user__role=User.ROLE_STUDENT,
                user__is_active=True,
            )
        except StudentProfile.DoesNotExist:
            return None
        return profile.user


class StudentProvisionForm(forms.Form):
    """Validate the first student provisioning workflow for tutors/admins."""

    fullname = forms.CharField(max_length=255)
    email = forms.EmailField()
    school_name = forms.CharField(max_length=255)
    registration_number = forms.CharField(max_length=100)

    def __init__(self, *args, tutor=None, **kwargs):
        self.tutor = tutor
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_registration_number(self):
        registration_number = self.cleaned_data["registration_number"].strip()
        if self.tutor and StudentProfile.objects.filter(
            tutor=self.tutor,
            registration_number=registration_number,
        ).exists():
            raise forms.ValidationError("This registration number already exists for your students.")
        return registration_number


class ClassroomForm(forms.Form):
    """Validate tutor classroom create/edit input."""

    name = forms.CharField(max_length=255)

    def clean_name(self):
        return self.cleaned_data["name"].strip()


class StudentSearchForm(forms.Form):
    """Validate optional student search terms for tutor-owned lists."""

    q = forms.CharField(max_length=100, required=False)


class BulkStudentImportForm(forms.Form):
    """Validate CSV/XLSX uploads for tutor student provisioning."""

    classroom_id = forms.IntegerField(required=False)
    file = forms.FileField()

    def __init__(self, *args, tutor=None, **kwargs):
        self.tutor = tutor
        super().__init__(*args, **kwargs)

    def clean_file(self):
        upload = self.cleaned_data["file"]
        name = upload.name.lower()
        if not name.endswith((".csv", ".xlsx")):
            raise forms.ValidationError("Upload a CSV or Excel .xlsx file.")
        return upload

    def clean_classroom_id(self):
        classroom_id = self.cleaned_data.get("classroom_id")
        if not classroom_id:
            return None
        if not self.tutor:
            raise forms.ValidationError("Tutor context is required.")
        if not Classroom.objects.filter(id=classroom_id, tutor=self.tutor).exists():
            raise forms.ValidationError("Classroom was not found.")
        return classroom_id


class AssessmentForm(forms.Form):
    """Validate core assessment builder settings."""

    classroom_id = forms.IntegerField()
    title = forms.CharField(max_length=255)
    assessment_type = forms.ChoiceField(choices=Exam.ASSESSMENT_TYPE_CHOICES)
    instructions = forms.CharField(required=False, widget=forms.Textarea)
    start_time = forms.DateTimeField(required=False, input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"])
    end_time = forms.DateTimeField(required=False, input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"])
    duration_minutes = forms.IntegerField(min_value=1)
    total_marks = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2)
    pass_mark = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2)
    attempts_allowed = forms.IntegerField(min_value=1)
    back_btn_enabled = forms.BooleanField(required=False)
    allow_late_submission = forms.BooleanField(required=False)
    show_results_immediately = forms.BooleanField(required=False)
    show_answers = forms.BooleanField(required=False)
    randomize_questions = forms.BooleanField(required=False)
    randomize_choices = forms.BooleanField(required=False)
    proctoring_enabled = forms.BooleanField(required=False)
    disable_copy_paste = forms.BooleanField(required=False)
    disable_right_click = forms.BooleanField(required=False)
    disable_text_selection = forms.BooleanField(required=False)
    detect_tab_switch = forms.BooleanField(required=False)
    detect_window_blur = forms.BooleanField(required=False)
    require_fullscreen = forms.BooleanField(required=False)
    detect_fullscreen_exit = forms.BooleanField(required=False)
    detect_refresh = forms.BooleanField(required=False)
    max_violation_warnings = forms.IntegerField(min_value=1, required=False)
    auto_submit_on_violation = forms.BooleanField(required=False)
    auto_disqualify_on_violation = forms.BooleanField(required=False)

    def __init__(self, *args, tutor=None, **kwargs):
        self.tutor = tutor
        super().__init__(*args, **kwargs)

    def clean_classroom_id(self):
        classroom_id = self.cleaned_data["classroom_id"]
        if not Classroom.objects.filter(id=classroom_id, tutor=self.tutor, is_archived=False).exists():
            raise forms.ValidationError("Classroom was not found.")
        return classroom_id

    def clean(self):
        cleaned = super().clean()
        start_time = cleaned.get("start_time")
        end_time = cleaned.get("end_time")
        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("End time must be after start time.")
        if cleaned.get("pass_mark", 0) > cleaned.get("total_marks", 0):
            raise forms.ValidationError("Pass mark cannot be greater than total marks.")
        return cleaned


class QuestionSectionForm(forms.Form):
    """Validate assessment section details."""

    title = forms.CharField(max_length=255)
    instructions = forms.CharField(required=False, widget=forms.Textarea)
    order = forms.IntegerField(min_value=0, initial=0)


class QuestionForm(forms.Form):
    """Validate question builder input and up to six dynamic choices."""

    section_id = forms.IntegerField(required=False)
    question_type = forms.ChoiceField(choices=Question.QUESTION_TYPE_CHOICES)
    text = forms.CharField(widget=forms.Textarea)
    explanation = forms.CharField(required=False, widget=forms.Textarea)
    media_url = forms.URLField(required=False)
    marks = forms.DecimalField(min_value=0, max_digits=8, decimal_places=2)
    correct_labels = forms.CharField(max_length=100, required=False)
    order = forms.IntegerField(min_value=0, initial=0)
    reusable_in_bank = forms.BooleanField(required=False)
    choice_a = forms.CharField(required=False)
    choice_b = forms.CharField(required=False)
    choice_c = forms.CharField(required=False)
    choice_d = forms.CharField(required=False)
    choice_e = forms.CharField(required=False)
    choice_f = forms.CharField(required=False)

    def __init__(self, *args, exam=None, **kwargs):
        self.exam = exam
        super().__init__(*args, **kwargs)

    def clean_section_id(self):
        section_id = self.cleaned_data.get("section_id")
        if not section_id:
            return None
        if not self.exam or not QuestionSection.objects.filter(id=section_id, exam=self.exam).exists():
            raise forms.ValidationError("Section was not found.")
        return section_id

    def clean(self):
        cleaned = super().clean()
        question_type = cleaned.get("question_type")
        choice_values = [
            cleaned.get("choice_a"),
            cleaned.get("choice_b"),
            cleaned.get("choice_c"),
            cleaned.get("choice_d"),
            cleaned.get("choice_e"),
            cleaned.get("choice_f"),
        ]
        has_choices = any(value for value in choice_values)
        if question_type in [Question.TYPE_SINGLE_CHOICE, Question.TYPE_MULTIPLE_CHOICE, Question.TYPE_TRUE_FALSE] and not has_choices:
            raise forms.ValidationError("Choice questions require at least one choice.")
        return cleaned


class BulkQuestionImportForm(forms.Form):
    """Validate CSV/XLSX question uploads."""

    file = forms.FileField()

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if not upload.name.lower().endswith((".csv", ".xlsx")):
            raise forms.ValidationError("Upload a CSV or Excel .xlsx file.")
        return upload


class BankQuestionSelectForm(forms.Form):
    """Validate adding a reusable bank question to an assessment."""

    bank_item_id = forms.IntegerField()

    def __init__(self, *args, tutor=None, **kwargs):
        self.tutor = tutor
        super().__init__(*args, **kwargs)

    def clean_bank_item_id(self):
        bank_item_id = self.cleaned_data["bank_item_id"]
        if not QuestionBankItem.objects.filter(id=bank_item_id, tutor=self.tutor).exists():
            raise forms.ValidationError("Question bank item was not found.")
        return bank_item_id


class StudentTodoForm(forms.Form):
    """Validate student-created todo items."""

    title = forms.CharField(max_length=255)
    notes = forms.CharField(required=False, widget=forms.Textarea)
    due_at = forms.DateTimeField(required=False, input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"])
    assessment_id = forms.IntegerField(required=False)

    def __init__(self, *args, student=None, **kwargs):
        self.student = student
        super().__init__(*args, **kwargs)

    def clean_title(self):
        return self.cleaned_data["title"].strip()

    def clean_assessment_id(self):
        assessment_id = self.cleaned_data.get("assessment_id")
        if not assessment_id:
            return None
        if not self.student:
            raise forms.ValidationError("Student context is required.")
        if not Exam.objects.filter(
            id=assessment_id,
            status=Exam.STATUS_PUBLISHED,
            classroom__students=self.student,
        ).exists():
            raise forms.ValidationError("Assessment was not found.")
        return assessment_id
