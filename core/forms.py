from django import forms
from django.contrib.auth import authenticate

from .models import Classroom, StudentProfile, User


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
