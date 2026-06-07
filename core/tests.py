from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Choice, Classroom, Exam, Invoice, MpesaTransaction, Payment, ProctorLog, Question, QuestionBankItem, StudentAnswer, StudentNotification, StudentProfile, StudentReminder, StudentTodo, Submission, SubscriptionPlan, TutorProfile, TutorSubscription, User
from .services import create_assessment, create_classroom, create_mpesa_payment_attempt, create_student_account, create_tutor_account, get_or_create_assessment_invoice, get_or_start_submission, get_student_assessment_overview, handle_mpesa_stk_callback, mark_invoice_paid, record_proctor_violation, save_submission_answers, submit_assessment_attempt


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


class AssessmentBuilderTests(TestCase):
    """Cover Phase 5 assessment builder ownership and question workflows."""

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
        self.classroom = create_classroom(tutor=self.tutor, name="Form 2A")
        self.other_classroom = create_classroom(tutor=self.other_tutor, name="Private Class")

    def assessment_payload(self, **overrides):
        data = {
            "classroom_id": self.classroom.id,
            "title": "Midterm Test",
            "assessment_type": Exam.TYPE_TEST,
            "instructions": "Answer all questions.",
            "duration_minutes": 60,
            "total_marks": "0",
            "pass_mark": "0",
            "attempts_allowed": 1,
            "back_btn_enabled": "on",
            "show_results_immediately": "on",
            "show_answers": "on",
        }
        data.update(overrides)
        return data

    def test_tutor_can_create_draft_assessment(self):
        self.client.force_login(self.tutor)

        response = self.client.post(reverse("assessment_create"), self.assessment_payload())

        exam = Exam.objects.get(title="Midterm Test")
        self.assertRedirects(response, reverse("assessment_detail", args=[exam.id]))
        self.assertEqual(exam.status, Exam.STATUS_DRAFT)
        self.assertEqual(exam.classroom, self.classroom)

    def test_tutor_cannot_access_another_tutors_assessment(self):
        exam = create_assessment(tutor=self.other_tutor, data={
            "classroom_id": self.other_classroom.id,
            "title": "Private Test",
            "assessment_type": Exam.TYPE_TEST,
            "instructions": "",
            "duration_minutes": 60,
            "total_marks": 0,
            "pass_mark": 0,
            "attempts_allowed": 1,
            "back_btn_enabled": True,
            "allow_late_submission": False,
            "show_results_immediately": True,
            "show_answers": True,
            "randomize_questions": False,
            "randomize_choices": False,
        })
        self.client.force_login(self.tutor)

        response = self.client.get(reverse("assessment_detail", args=[exam.id]))

        self.assertEqual(response.status_code, 404)

    def test_tutor_can_add_section_and_question_with_choices(self):
        exam = create_assessment(tutor=self.tutor, data={
            "classroom_id": self.classroom.id,
            "title": "Midterm Test",
            "assessment_type": Exam.TYPE_TEST,
            "instructions": "",
            "duration_minutes": 60,
            "total_marks": 0,
            "pass_mark": 0,
            "attempts_allowed": 1,
            "back_btn_enabled": True,
            "allow_late_submission": False,
            "show_results_immediately": True,
            "show_answers": True,
            "randomize_questions": False,
            "randomize_choices": False,
        })
        self.client.force_login(self.tutor)

        section_response = self.client.post(
            reverse("assessment_add_section", args=[exam.id]),
            {"title": "Section A", "instructions": "MCQs", "order": 1},
        )
        section = exam.sections.get(title="Section A")
        question_response = self.client.post(
            reverse("assessment_add_question", args=[exam.id]),
            {
                "section_id": section.id,
                "question_type": Question.TYPE_SINGLE_CHOICE,
                "text": "What is 2 + 2?",
                "marks": "2",
                "correct_labels": "A",
                "order": 1,
                "choice_a": "4",
                "choice_b": "3",
                "reusable_in_bank": "on",
            },
        )
        exam.refresh_from_db()

        self.assertRedirects(section_response, reverse("assessment_detail", args=[exam.id]))
        self.assertRedirects(question_response, reverse("assessment_detail", args=[exam.id]))
        question = exam.questions.get(text="What is 2 + 2?")
        self.assertEqual(question.choices.count(), 2)
        self.assertEqual(exam.total_marks, 2)
        self.assertTrue(QuestionBankItem.objects.filter(tutor=self.tutor).exists())

    def test_bulk_question_import_creates_questions(self):
        exam = create_assessment(tutor=self.tutor, data={
            "classroom_id": self.classroom.id,
            "title": "Midterm Test",
            "assessment_type": Exam.TYPE_TEST,
            "instructions": "",
            "duration_minutes": 60,
            "total_marks": 0,
            "pass_mark": 0,
            "attempts_allowed": 1,
            "back_btn_enabled": True,
            "allow_late_submission": False,
            "show_results_immediately": True,
            "show_answers": True,
            "randomize_questions": False,
            "randomize_choices": False,
        })
        self.client.force_login(self.tutor)
        upload = SimpleUploadedFile(
            "questions.csv",
            b"section,question_type,text,marks,correct_labels,choice_a,choice_b\n"
            b"Section A,single_choice,What is 1+1?,1,A,2,3\n"
            b"Section A,short_answer,Name Kenya capital,2,,,\n",
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("assessment_import_questions", args=[exam.id]),
            {"file": upload},
        )

        self.assertRedirects(response, reverse("assessment_detail", args=[exam.id]))
        self.assertEqual(exam.questions.count(), 2)
        exam.refresh_from_db()
        self.assertEqual(exam.total_marks, 3)

    def test_publish_requires_questions_then_succeeds(self):
        exam = create_assessment(tutor=self.tutor, data={
            "classroom_id": self.classroom.id,
            "title": "Midterm Test",
            "assessment_type": Exam.TYPE_TEST,
            "instructions": "",
            "duration_minutes": 60,
            "total_marks": 0,
            "pass_mark": 0,
            "attempts_allowed": 1,
            "back_btn_enabled": True,
            "allow_late_submission": False,
            "show_results_immediately": True,
            "show_answers": True,
            "randomize_questions": False,
            "randomize_choices": False,
        })
        self.client.force_login(self.tutor)

        empty_response = self.client.post(reverse("assessment_publish", args=[exam.id]))
        exam.refresh_from_db()
        self.assertRedirects(empty_response, reverse("assessment_detail", args=[exam.id]))
        self.assertEqual(exam.status, Exam.STATUS_DRAFT)

        self.client.post(
            reverse("assessment_add_question", args=[exam.id]),
            {
                "question_type": Question.TYPE_SHORT_ANSWER,
                "text": "Explain photosynthesis.",
                "marks": "5",
                "order": 1,
            },
        )
        publish_response = self.client.post(reverse("assessment_publish", args=[exam.id]))
        exam.refresh_from_db()

        self.assertRedirects(publish_response, reverse("assessment_detail", args=[exam.id]))
        self.assertEqual(exam.status, Exam.STATUS_PUBLISHED)


class BillingWorkflowTests(TestCase):
    """Cover Phase 6 tutor billing, subscription, and payment reconciliation."""

    def setUp(self):
        self.tutor = create_tutor_account(
            fullname="Tutor One",
            email="billing-tutor@example.com",
            password="StrongPass123!",
        )
        self.classroom = create_classroom(tutor=self.tutor, name="Form 2A")
        for index in range(3):
            student, _ = create_student_account(
                tutor=self.tutor,
                fullname=f"Student {index}",
                email=f"student{index}@example.com",
                school_name="Test School",
                registration_number=f"ADM-00{index}",
            )
            self.classroom.students.add(student)

    def create_ready_assessment(self):
        exam = create_assessment(tutor=self.tutor, data={
            "classroom_id": self.classroom.id,
            "title": "Billing Test",
            "assessment_type": Exam.TYPE_TEST,
            "instructions": "",
            "duration_minutes": 60,
            "total_marks": 0,
            "pass_mark": 0,
            "attempts_allowed": 1,
            "back_btn_enabled": True,
            "allow_late_submission": False,
            "show_results_immediately": True,
            "show_answers": True,
            "randomize_questions": False,
            "randomize_choices": False,
        })
        Question.objects.create(
            exam=exam,
            question_type=Question.TYPE_SHORT_ANSWER,
            text="Explain evaporation.",
            marks=5,
            order=1,
        )
        return exam

    def test_assessment_invoice_uses_five_shillings_per_student(self):
        exam = self.create_ready_assessment()

        invoice = get_or_create_assessment_invoice(tutor=self.tutor, exam=exam)

        self.assertEqual(invoice.quantity, 3)
        self.assertEqual(invoice.unit_amount, 5)
        self.assertEqual(invoice.total_amount, 15)

    @override_settings(DEBUG=True)
    def test_publish_redirects_to_invoice_until_paid(self):
        exam = self.create_ready_assessment()
        self.client.force_login(self.tutor)

        response = self.client.post(reverse("assessment_publish", args=[exam.id]))
        exam.refresh_from_db()
        invoice = Invoice.objects.get(assessment=exam)

        self.assertRedirects(response, reverse("invoice_detail", args=[invoice.id]))
        self.assertEqual(exam.status, Exam.STATUS_DRAFT)

        confirm_response = self.client.post(reverse("invoice_dev_confirm", args=[invoice.id]))
        exam.refresh_from_db()
        invoice.refresh_from_db()

        self.assertRedirects(confirm_response, reverse("invoice_detail", args=[invoice.id]))
        self.assertEqual(invoice.status, Invoice.STATUS_PAID)
        self.assertEqual(exam.status, Exam.STATUS_PUBLISHED)

    def test_active_subscription_allows_publish_without_assessment_invoice(self):
        plan = SubscriptionPlan.objects.create(
            name="Monthly Standard",
            duration_months=1,
            price=500,
            anti_cheating_level=SubscriptionPlan.ANTI_CHEATING_STANDARD,
        )
        TutorSubscription.objects.create(
            tutor=self.tutor,
            plan=plan,
            status=TutorSubscription.STATUS_ACTIVE,
            starts_at=timezone.now() - timedelta(days=1),
            ends_at=timezone.now() + timedelta(days=30),
        )
        exam = self.create_ready_assessment()
        self.client.force_login(self.tutor)

        response = self.client.post(reverse("assessment_publish", args=[exam.id]))
        exam.refresh_from_db()

        self.assertRedirects(response, reverse("assessment_detail", args=[exam.id]))
        self.assertEqual(exam.status, Exam.STATUS_PUBLISHED)
        self.assertFalse(Invoice.objects.filter(assessment=exam).exists())

    def test_subscription_invoice_payment_activates_subscription(self):
        plan = SubscriptionPlan.objects.create(
            name="Quarterly Strict",
            duration_months=3,
            price=1200,
            discount_percent=10,
            anti_cheating_level=SubscriptionPlan.ANTI_CHEATING_STRICT,
        )
        self.client.force_login(self.tutor)

        response = self.client.post(reverse("start_subscription", args=[plan.id]))
        invoice = Invoice.objects.get(subscription_plan=plan, tutor=self.tutor)
        mark_invoice_paid(invoice=invoice, method=Payment.METHOD_MANUAL, provider_reference="TEST")

        self.assertRedirects(response, reverse("invoice_detail", args=[invoice.id]))
        self.assertTrue(TutorSubscription.objects.filter(tutor=self.tutor, plan=plan, status=TutorSubscription.STATUS_ACTIVE).exists())
        self.assertEqual(invoice.total_amount, 1080)

    def test_mpesa_callback_marks_invoice_paid_idempotently(self):
        exam = self.create_ready_assessment()
        invoice = get_or_create_assessment_invoice(tutor=self.tutor, exam=exam)
        payment = create_mpesa_payment_attempt(invoice=invoice, phone_number="254712345678")
        payment.checkout_request_id = "ws_CO_123"
        payment.save(update_fields=["checkout_request_id"])
        payload = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "29115-34620561-1",
                    "CheckoutRequestID": "ws_CO_123",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 15},
                            {"Name": "MpesaReceiptNumber", "Value": "RKTQDM7W6S"},
                            {"Name": "PhoneNumber", "Value": 254712345678},
                        ]
                    },
                }
            }
        }

        handle_mpesa_stk_callback(payload)
        handle_mpesa_stk_callback(payload)
        invoice.refresh_from_db()
        payment.refresh_from_db()

        self.assertEqual(invoice.status, Invoice.STATUS_PAID)
        self.assertEqual(payment.status, Payment.STATUS_SUCCESSFUL)
        self.assertEqual(MpesaTransaction.objects.filter(checkout_request_id="ws_CO_123").count(), 1)


class StudentDashboardWorkflowTests(TestCase):
    """Cover Phase 7 student visibility, todos, reminders, and notifications."""

    def setUp(self):
        self.tutor = create_tutor_account(
            fullname="Tutor One",
            email="phase7-tutor@example.com",
            password="StrongPass123!",
        )
        self.other_tutor = create_tutor_account(
            fullname="Other Tutor",
            email="phase7-other@example.com",
            password="StrongPass123!",
        )
        self.classroom = create_classroom(tutor=self.tutor, name="Form 3A")
        self.other_classroom = create_classroom(tutor=self.other_tutor, name="Other Class")
        self.student, _ = create_student_account(
            tutor=self.tutor,
            fullname="Student One",
            email="phase7-student@example.com",
            school_name="Test School",
            registration_number="ADM-777",
        )
        self.other_student, _ = create_student_account(
            tutor=self.other_tutor,
            fullname="Student Two",
            email="phase7-student2@example.com",
            school_name="Other School",
            registration_number="ADM-888",
        )
        self.classroom.students.add(self.student)
        self.other_classroom.students.add(self.other_student)

    def create_assessment_for(self, *, classroom, title, status=Exam.STATUS_PUBLISHED, start_time=None, end_time=None, allow_late_submission=False):
        exam = Exam.objects.create(
            classroom=classroom,
            title=title,
            assessment_type=Exam.TYPE_TEST,
            status=status,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=45,
            allow_late_submission=allow_late_submission,
        )
        Question.objects.create(
            exam=exam,
            question_type=Question.TYPE_SHORT_ANSWER,
            text=f"Question for {title}",
            marks=5,
            order=1,
        )
        return exam

    def test_student_dashboard_shows_only_assigned_published_assessments(self):
        now = timezone.now()
        own_exam = self.create_assessment_for(
            classroom=self.classroom,
            title="Assigned Active Test",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=2),
        )
        self.create_assessment_for(
            classroom=self.classroom,
            title="Draft Hidden Test",
            status=Exam.STATUS_DRAFT,
        )
        self.create_assessment_for(
            classroom=self.other_classroom,
            title="Other Student Test",
        )
        self.client.force_login(self.student)

        response = self.client.get(reverse("student_dashboard"))

        self.assertContains(response, own_exam.title)
        self.assertNotContains(response, "Draft Hidden Test")
        self.assertNotContains(response, "Other Student Test")
        self.assertTrue(StudentNotification.objects.filter(student=self.student, assessment=own_exam).exists())

    def test_student_assessments_are_grouped_by_status(self):
        now = timezone.now()
        active = self.create_assessment_for(
            classroom=self.classroom,
            title="Active Test",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=2),
        )
        pending = self.create_assessment_for(
            classroom=self.classroom,
            title="Pending Test",
            start_time=now + timedelta(days=1),
        )
        overdue = self.create_assessment_for(
            classroom=self.classroom,
            title="Overdue Test",
            end_time=now - timedelta(hours=1),
        )
        completed = self.create_assessment_for(
            classroom=self.classroom,
            title="Completed Test",
        )
        Submission.objects.create(student=self.student, exam=completed, completed=True, score=4)

        overview = get_student_assessment_overview(student=self.student)

        self.assertIn(active, overview["active"])
        self.assertIn(pending, overview["pending"])
        self.assertIn(overdue, overview["overdue"])
        self.assertIn(completed, overview["completed"])

    def test_student_can_create_todo_and_reminder(self):
        exam = self.create_assessment_for(classroom=self.classroom, title="Todo Linked Test")
        due_at = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("student_dashboard"),
            {
                "form_action": "create_todo",
                "title": "Revise algebra",
                "notes": "Chapter 4",
                "due_at": due_at,
                "assessment_id": exam.id,
            },
        )
        todo = StudentTodo.objects.get(student=self.student, title="Revise algebra")

        self.assertRedirects(response, reverse("student_dashboard"))
        self.assertEqual(todo.assessment, exam)
        self.assertTrue(StudentReminder.objects.filter(student=self.student, todo=todo).exists())

    def test_student_can_complete_only_own_todo(self):
        own_todo = StudentTodo.objects.create(student=self.student, title="Own todo")
        other_todo = StudentTodo.objects.create(student=self.other_student, title="Other todo")
        self.client.force_login(self.student)

        own_response = self.client.post(
            reverse("student_dashboard"),
            {"form_action": "complete_todo", "todo_id": own_todo.id},
        )
        forbidden_response = self.client.post(
            reverse("student_dashboard"),
            {"form_action": "complete_todo", "todo_id": other_todo.id},
        )
        own_todo.refresh_from_db()
        other_todo.refresh_from_db()

        self.assertRedirects(own_response, reverse("student_dashboard"))
        self.assertTrue(own_todo.is_completed)
        self.assertEqual(forbidden_response.status_code, 404)
        self.assertFalse(other_todo.is_completed)

    def test_student_can_mark_notification_read(self):
        notification = StudentNotification.objects.create(
            student=self.student,
            title="Assessment ready",
            message="Start when ready.",
            notification_type=StudentNotification.TYPE_ASSESSMENT,
        )
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("student_dashboard"),
            {"form_action": "mark_notification_read", "notification_id": notification.id},
        )
        notification.refresh_from_db()

        self.assertRedirects(response, reverse("student_dashboard"))
        self.assertTrue(notification.is_read)


class ExamTakingEngineTests(TestCase):
    """Cover Phase 8 student attempt access, saving, submission, and grading."""

    def setUp(self):
        self.tutor = create_tutor_account(
            fullname="Exam Tutor",
            email="phase8-tutor@example.com",
            password="StrongPass123!",
        )
        self.classroom = create_classroom(tutor=self.tutor, name="Phase 8 Class")
        self.student, _ = create_student_account(
            tutor=self.tutor,
            fullname="Exam Student",
            email="phase8-student@example.com",
            school_name="Test School",
            registration_number="P8-001",
        )
        self.classroom.students.add(self.student)

    def create_objective_exam(self, **overrides):
        data = {
            "title": "Objective Test",
            "assessment_type": Exam.TYPE_TEST,
            "status": Exam.STATUS_PUBLISHED,
            "start_time": timezone.now() - timedelta(minutes=5),
            "end_time": timezone.now() + timedelta(days=1),
            "duration_minutes": 30,
            "total_marks": 0,
            "pass_mark": 0,
            "attempts_allowed": 1,
            "show_results_immediately": True,
        }
        data.update(overrides)
        exam = Exam.objects.create(classroom=self.classroom, **data)
        q1 = Question.objects.create(
            exam=exam,
            question_type=Question.TYPE_SINGLE_CHOICE,
            text="2 + 2?",
            marks=2,
            correct_labels="A",
            order=1,
        )
        Choice.objects.create(question=q1, label="A", text="4")
        Choice.objects.create(question=q1, label="B", text="3")
        q2 = Question.objects.create(
            exam=exam,
            question_type=Question.TYPE_MULTIPLE_CHOICE,
            text="Prime numbers",
            marks=3,
            correct_labels="A,C",
            order=2,
        )
        Choice.objects.create(question=q2, label="A", text="2")
        Choice.objects.create(question=q2, label="B", text="4")
        Choice.objects.create(question=q2, label="C", text="5")
        exam.total_marks = 5
        exam.save(update_fields=["total_marks"])
        return exam

    def test_student_can_start_assigned_active_assessment(self):
        exam = self.create_objective_exam()

        submission = get_or_start_submission(student=self.student, exam=exam)

        self.assertEqual(submission.student, self.student)
        self.assertEqual(submission.exam, exam)
        self.assertFalse(submission.completed)
        self.assertIsNotNone(submission.expires_at)

    def test_student_cannot_start_unassigned_or_closed_assessment(self):
        other_tutor = create_tutor_account(
            fullname="Other Tutor",
            email="phase8-other@example.com",
            password="StrongPass123!",
        )
        other_classroom = create_classroom(tutor=other_tutor, name="Other Class")
        unassigned = Exam.objects.create(
            classroom=other_classroom,
            title="Private Exam",
            status=Exam.STATUS_PUBLISHED,
            duration_minutes=30,
        )
        closed = self.create_objective_exam(end_time=timezone.now() - timedelta(minutes=1))

        with self.assertRaises(PermissionError):
            get_or_start_submission(student=self.student, exam=unassigned)
        with self.assertRaises(ValueError):
            get_or_start_submission(student=self.student, exam=closed)

    def test_save_answers_and_submit_grades_objective_questions(self):
        exam = self.create_objective_exam()
        submission = get_or_start_submission(student=self.student, exam=exam)
        questions = list(exam.questions.order_by("order"))

        save_submission_answers(
            submission=submission,
            answer_data={
                str(questions[0].id): "A",
                str(questions[1].id): ["C", "A"],
            },
        )
        submitted = submit_assessment_attempt(student=self.student, submission=submission)

        self.assertTrue(submitted.completed)
        self.assertEqual(submitted.score, 5.0)
        self.assertEqual(StudentAnswer.objects.filter(submission=submission, is_correct=True).count(), 2)

    def test_attempt_limit_is_enforced_after_completion(self):
        exam = self.create_objective_exam(attempts_allowed=1)
        submission = get_or_start_submission(student=self.student, exam=exam)
        submit_assessment_attempt(student=self.student, submission=submission)

        with self.assertRaises(ValueError):
            get_or_start_submission(student=self.student, exam=exam)

    def test_student_can_take_assessment_from_dashboard_link(self):
        exam = self.create_objective_exam()
        self.client.force_login(self.student)

        response = self.client.get(reverse("student_assessment_start", args=[exam.id]))
        submission = Submission.objects.get(student=self.student, exam=exam)

        self.assertRedirects(response, reverse("student_assessment_take", args=[submission.id]))

    def test_posting_attempt_submits_and_shows_result(self):
        exam = self.create_objective_exam()
        submission = get_or_start_submission(student=self.student, exam=exam)
        questions = list(exam.questions.order_by("order"))
        self.client.force_login(self.student)

        response = self.client.post(
            reverse("student_assessment_take", args=[submission.id]),
            {
                "form_action": "submit",
                f"answer_{questions[0].id}": "A",
                f"answer_{questions[1].id}": ["A", "C"],
            },
        )
        submission.refresh_from_db()

        self.assertRedirects(response, reverse("student_assessment_result", args=[submission.id]))
        self.assertTrue(submission.completed)
        self.assertEqual(submission.score, 5.0)


class ProctoringWorkflowTests(TestCase):
    """Cover Phase 9 proctoring rules, violation logging, and threshold actions."""

    def setUp(self):
        self.tutor = create_tutor_account(
            fullname="Proctor Tutor",
            email="phase9-tutor@example.com",
            password="StrongPass123!",
        )
        self.classroom = create_classroom(tutor=self.tutor, name="Phase 9 Class")
        self.student, _ = create_student_account(
            tutor=self.tutor,
            fullname="Proctor Student",
            email="phase9-student@example.com",
            school_name="Test School",
            registration_number="P9-001",
        )
        self.classroom.students.add(self.student)

    def create_proctored_exam(self, **overrides):
        data = {
            "classroom": self.classroom,
            "title": "Proctored Test",
            "assessment_type": Exam.TYPE_TEST,
            "status": Exam.STATUS_PUBLISHED,
            "start_time": timezone.now() - timedelta(minutes=5),
            "end_time": timezone.now() + timedelta(days=1),
            "duration_minutes": 30,
            "total_marks": 1,
            "attempts_allowed": 1,
            "proctoring_enabled": True,
            "disable_copy_paste": True,
            "detect_tab_switch": True,
            "max_violation_warnings": 2,
        }
        data.update(overrides)
        exam = Exam.objects.create(**data)
        Question.objects.create(
            exam=exam,
            question_type=Question.TYPE_SHORT_ANSWER,
            text="Explain integrity.",
            marks=1,
            order=1,
        )
        return exam

    def test_assessment_form_persists_proctoring_settings(self):
        self.client.force_login(self.tutor)

        response = self.client.post(
            reverse("assessment_create"),
            {
                "classroom_id": self.classroom.id,
                "title": "Integrity CAT",
                "assessment_type": Exam.TYPE_CAT,
                "duration_minutes": 45,
                "total_marks": "10",
                "pass_mark": "5",
                "attempts_allowed": 1,
                "proctoring_enabled": "on",
                "disable_copy_paste": "on",
                "disable_right_click": "on",
                "disable_text_selection": "on",
                "detect_tab_switch": "on",
                "detect_window_blur": "on",
                "require_fullscreen": "on",
                "detect_fullscreen_exit": "on",
                "detect_refresh": "on",
                "max_violation_warnings": 2,
                "auto_disqualify_on_violation": "on",
            },
        )
        exam = Exam.objects.get(title="Integrity CAT")

        self.assertRedirects(response, reverse("assessment_detail", args=[exam.id]))
        self.assertTrue(exam.proctoring_enabled)
        self.assertTrue(exam.disable_copy_paste)
        self.assertTrue(exam.auto_disqualify_on_violation)
        self.assertEqual(exam.max_violation_warnings, 2)

    def test_violation_logging_counts_without_threshold_action(self):
        exam = self.create_proctored_exam(max_violation_warnings=3)
        submission = get_or_start_submission(student=self.student, exam=exam)

        log, action = record_proctor_violation(
            student=self.student,
            submission=submission,
            violation_type=ProctorLog.TYPE_COPY,
            details="Copy attempted.",
        )

        self.assertEqual(log.violation_count, 1)
        self.assertFalse(action["disqualified"])
        self.assertFalse(action["submitted"])
        self.assertEqual(ProctorLog.objects.filter(submission=submission).count(), 1)

    def test_violation_threshold_can_disqualify_attempt(self):
        exam = self.create_proctored_exam(auto_disqualify_on_violation=True, max_violation_warnings=2)
        submission = get_or_start_submission(student=self.student, exam=exam)

        record_proctor_violation(student=self.student, submission=submission, violation_type=ProctorLog.TYPE_COPY)
        log, action = record_proctor_violation(student=self.student, submission=submission, violation_type=ProctorLog.TYPE_TAB_SWITCH)
        submission.refresh_from_db()

        self.assertTrue(action["disqualified"])
        self.assertTrue(log.triggered_disqualification)
        self.assertTrue(submission.completed)
        self.assertTrue(submission.is_disqualified)

    def test_violation_threshold_can_auto_submit_attempt(self):
        exam = self.create_proctored_exam(auto_submit_on_violation=True, max_violation_warnings=1)
        submission = get_or_start_submission(student=self.student, exam=exam)

        _, action = record_proctor_violation(student=self.student, submission=submission, violation_type=ProctorLog.TYPE_WINDOW_BLUR)
        submission.refresh_from_db()

        self.assertTrue(action["submitted"])
        self.assertTrue(submission.completed)
        self.assertFalse(submission.is_disqualified)

    def test_violation_endpoint_requires_valid_type_and_returns_action(self):
        exam = self.create_proctored_exam(auto_disqualify_on_violation=True, max_violation_warnings=1)
        submission = get_or_start_submission(student=self.student, exam=exam)
        self.client.force_login(self.student)

        invalid = self.client.post(
            reverse("student_proctor_violation", args=[submission.id]),
            data='{"violation_type": "BAD"}',
            content_type="application/json",
        )
        valid = self.client.post(
            reverse("student_proctor_violation", args=[submission.id]),
            data='{"violation_type": "TAB_SWITCH", "details": "Hidden"}',
            content_type="application/json",
        )
        submission.refresh_from_db()

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(valid.status_code, 200)
        self.assertTrue(valid.json()["disqualified"])
        self.assertTrue(submission.is_disqualified)
