from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Classroom, StudentProfile, TutorProfile, User
from .services import create_classroom, create_student_account, create_tutor_account


class AccountRoleTests(TestCase):
    """Cover account model, role routing, and portal entry behavior."""

    def test_tutor_registration_creates_tutor_profile(self):
        response = self.client.post(
            reverse("auth_page"),
            {
                "auth_mode": "register",
                "fullname": "Jane Tutor",
                "email": "jane@example.com",
                "phone_number": "0712345678",
                "institution_name": "Nairobi Academy",
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        user = User.objects.get(email="jane@example.com")
        self.assertEqual(user.role, User.ROLE_TUTOR)
        self.assertTrue(user.is_tutor)
        self.assertTrue(TutorProfile.objects.filter(user=user).exists())

    def test_tutor_can_provision_student_account(self):
        tutor = create_tutor_account(
            fullname="Tutor One",
            email="tutor@example.com",
            password="StrongPass123!",
            institution_name="Test School",
        )
        self.client.force_login(tutor)

        response = self.client.post(
            reverse("tutor_dashboard"),
            {
                "form_action": "create_student",
                "fullname": "Student One",
                "email": "student@example.com",
                "school_name": "Test School",
                "registration_number": "ADM-001",
            },
        )

        self.assertEqual(response.status_code, 200)
        student = User.objects.get(email="student@example.com")
        profile = StudentProfile.objects.get(user=student)
        self.assertEqual(student.role, User.ROLE_STUDENT)
        self.assertEqual(profile.tutor, tutor)
        self.assertContains(response, "Temporary password")

    def test_student_can_login_with_registration_number(self):
        tutor = create_tutor_account(
            fullname="Tutor One",
            email="tutor@example.com",
            password="StrongPass123!",
        )
        create_student_account(
            tutor=tutor,
            fullname="Student One",
            email="student@example.com",
            school_name="Test School",
            registration_number="ADM-001",
        )

        response = self.client.post(
            reverse("auth_page"),
            {
                "auth_mode": "login",
                "email": "student@example.com",
                "password": "ADM-001",
            },
        )

        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        followup = self.client.get(reverse("dashboard"))
        self.assertRedirects(followup, reverse("student_dashboard"))

    def test_student_cannot_access_tutor_dashboard(self):
        tutor = create_tutor_account(
            fullname="Tutor One",
            email="tutor@example.com",
            password="StrongPass123!",
        )
        student, _ = create_student_account(
            tutor=tutor,
            fullname="Student One",
            email="student@example.com",
            school_name="Test School",
            registration_number="ADM-001",
        )
        self.client.force_login(student)

        response = self.client.get(reverse("tutor_dashboard"))

        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)

    def test_tutor_can_reset_owned_student_credentials(self):
        tutor = create_tutor_account(
            fullname="Tutor One",
            email="tutor@example.com",
            password="StrongPass123!",
        )
        student, old_password = create_student_account(
            tutor=tutor,
            fullname="Student One",
            email="student@example.com",
            school_name="Test School",
            registration_number="ADM-001",
        )
        self.client.force_login(tutor)

        response = self.client.post(reverse("reset_student_credentials", args=[student.id]))

        self.assertRedirects(response, reverse("tutor_dashboard"))
        student.refresh_from_db()
        self.assertFalse(student.check_password(old_password))

    def test_password_reset_page_is_available(self):
        response = self.client.get(reverse("password_reset"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset Password")

    def test_portal_landing_is_available_for_account_access(self):
        response = self.client.get(reverse("portal_landing"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aptitude Kenya Portal")
        self.assertContains(response, "Create tutor account")

    def test_authenticated_user_is_redirected_from_portal_to_dashboard(self):
        tutor = create_tutor_account(
            fullname="Tutor One",
            email="tutor@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(tutor)

        response = self.client.get(reverse("portal_landing"))

        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)


class TutorClassroomTests(TestCase):
    """Cover Phase 4 tutor classroom ownership and student workflows."""

    def setUp(self):
        self.tutor = create_tutor_account(
            fullname="Tutor One",
            email="tutor@example.com",
            password="StrongPass123!",
        )
        self.other_tutor = create_tutor_account(
            fullname="Tutor Two",
            email="other@example.com",
            password="StrongPass123!",
        )

    def test_tutor_can_create_classroom_from_dashboard(self):
        self.client.force_login(self.tutor)

        response = self.client.post(
            reverse("tutor_dashboard"),
            {"form_action": "create_classroom", "name": "Form 2A"},
        )

        self.assertRedirects(response, reverse("tutor_dashboard"))
        classroom = Classroom.objects.get(name="Form 2A")
        self.assertEqual(classroom.tutor, self.tutor)
        self.assertFalse(classroom.is_archived)

    def test_tutor_can_edit_and_archive_owned_classroom(self):
        classroom = create_classroom(tutor=self.tutor, name="Form 2A")
        self.client.force_login(self.tutor)

        edit_response = self.client.post(
            reverse("classroom_edit", args=[classroom.id]),
            {"name": "Form 2B"},
        )
        classroom.refresh_from_db()

        self.assertRedirects(edit_response, reverse("classroom_detail", args=[classroom.id]))
        self.assertEqual(classroom.name, "Form 2B")

        archive_response = self.client.post(reverse("classroom_archive", args=[classroom.id]))
        classroom.refresh_from_db()

        self.assertRedirects(archive_response, reverse("tutor_dashboard"))
        self.assertTrue(classroom.is_archived)

    def test_tutor_cannot_access_another_tutors_classroom(self):
        classroom = create_classroom(tutor=self.other_tutor, name="Private Class")
        self.client.force_login(self.tutor)

        response = self.client.get(reverse("classroom_detail", args=[classroom.id]))

        self.assertEqual(response.status_code, 404)

    def test_classroom_detail_can_create_and_assign_student(self):
        classroom = create_classroom(tutor=self.tutor, name="Form 2A")
        self.client.force_login(self.tutor)

        response = self.client.post(
            reverse("classroom_detail", args=[classroom.id]),
            {
                "form_action": "create_student",
                "fullname": "Student One",
                "email": "student@example.com",
                "school_name": "Test School",
                "registration_number": "ADM-001",
            },
        )

        self.assertEqual(response.status_code, 200)
        student = User.objects.get(email="student@example.com")
        self.assertTrue(classroom.students.filter(id=student.id).exists())
        self.assertContains(response, "Temporary password")

    def test_bulk_import_creates_students_and_assigns_classroom(self):
        classroom = create_classroom(tutor=self.tutor, name="Form 2A")
        self.client.force_login(self.tutor)
        upload = SimpleUploadedFile(
            "students.csv",
            b"fullname,email,school_name,registration_number\n"
            b"Student One,student1@example.com,Test School,ADM-001\n"
            b"Student Two,student2@example.com,Test School,ADM-002\n",
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("classroom_detail", args=[classroom.id]),
            {
                "form_action": "bulk_import",
                "classroom_id": classroom.id,
                "file": upload,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(StudentProfile.objects.filter(tutor=self.tutor).count(), 2)
        self.assertEqual(classroom.students.count(), 2)
        self.assertContains(response, "Imported 2 students.")

    def test_student_search_filters_tutor_owned_students(self):
        create_student_account(
            tutor=self.tutor,
            fullname="Alpha Student",
            email="alpha@example.com",
            school_name="Test School",
            registration_number="ADM-001",
        )
        create_student_account(
            tutor=self.tutor,
            fullname="Beta Student",
            email="beta@example.com",
            school_name="Test School",
            registration_number="ADM-002",
        )
        self.client.force_login(self.tutor)

        response = self.client.get(reverse("tutor_dashboard"), {"q": "Alpha"})

        self.assertContains(response, "Alpha Student")
        self.assertNotContains(response, "Beta Student")
