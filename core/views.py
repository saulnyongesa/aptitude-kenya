import json
import csv
import json
from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from .forms import AssessmentForm, BankQuestionSelectForm, BulkQuestionImportForm, BulkStudentImportForm, ClassroomForm, LoginForm, QuestionForm, QuestionSectionForm, StudentProvisionForm, StudentSearchForm, StudentTodoForm, TutorRegistrationForm
from .models import Classroom, Exam, Invoice, Payment, ProctorLog, QuestionBankItem, SiteStatistic, ContactMessage, StudentNotification, StudentProfile, StudentTodo, Submission, SubscriptionPlan, User
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from .decorators import role_required
from .services import activate_subscription_from_invoice, add_bank_question_to_assessment, archive_classroom, assign_student_to_classroom, assessment_can_publish_without_invoice, build_attempt_context, complete_student_todo, create_assessment, create_classroom, create_mpesa_payment_attempt, create_question_from_form, create_question_section, create_student_account, create_student_todo, create_subscription_invoice, create_tutor_account, estimate_subscription_upgrade_credit, get_active_subscription, get_admin_report_context, get_assessment_report_context, get_classroom_report_context, get_or_create_assessment_invoice, get_or_start_submission, get_student_assessment_for_taking, get_student_dashboard_context, get_student_report_context, get_tutor_report_context, handle_mpesa_stk_callback, import_questions_from_file, import_students_from_file, mark_invoice_paid, mark_student_notification_read, publish_assessment, record_proctor_violation, reset_student_credentials, save_submission_answers, submit_assessment_attempt, tutor_assessment_export_rows, update_assessment, update_classroom

def index(request):
    # Fetch stats from the SiteStatistic model (Singleton-style)
    stats = SiteStatistic.objects.first()
    
    context = {
        'tutor_count': stats.tutor_count if stats else 0,
        'student_count': stats.student_count if stats else 0,
        'classroom_count': stats.classroom_count if stats else 0,
        'exam_count': stats.exam_count if stats else 0,
    }
    return render(request, 'index.html', context)


def portal_landing(request):
    """Render the dedicated account portal entry page.

    This page is intentionally separate from the marketing homepage so tutors
    and students have a direct, uncluttered place to begin their work.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'portal/index.html')

def send_message(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message_text = request.POST.get('message')
        
        ContactMessage.objects.create(
            name=name,
            email=email,
            message=message_text
        )
        return JsonResponse({'message': 'Thank you! Your message has been received.'})
    return JsonResponse({'message': 'Invalid request'}, status=400)

def auth_view(request):
    if request.method == 'POST':
        auth_mode = request.POST.get('auth_mode', 'login')

        if auth_mode == 'register':
            form = TutorRegistrationForm(request.POST)
            if form.is_valid():
                user = create_tutor_account(
                    fullname=form.cleaned_data['fullname'],
                    email=form.cleaned_data['email'],
                    phone_number=form.cleaned_data.get('phone_number', ''),
                    institution_name=form.cleaned_data.get('institution_name', ''),
                    password=form.cleaned_data['password'],
                )
                login(request, user)
                messages.success(request, "Tutor account created successfully.")
                return redirect('dashboard')
        else:
            form = LoginForm(request.POST)
            if form.is_valid():
                login(request, form.cleaned_data['user'])
                return redirect('dashboard')

        for error in form.errors.get('__all__', []):
            messages.error(request, error)
        for field_errors in form.errors.values():
            for error in field_errors:
                if error not in form.errors.get('__all__', []):
                    messages.error(request, error)

    return render(
        request,
        'registration/login.html',
        {'initial_mode': request.GET.get('mode', 'login')},
    )

def logout_view(request):
    logout(request)
    return redirect('index')


@login_required
def dashboard(request):
    """Send a signed-in user to the correct dashboard for their role."""
    if request.user.is_platform_admin:
        return redirect('admin_dashboard')
    if request.user.role == User.ROLE_TUTOR:
        return redirect('tutor_dashboard')
    if request.user.role == User.ROLE_STUDENT:
        return redirect('student_dashboard')
    messages.error(request, "Your account role is not configured.")
    return redirect('index')


@role_required(User.ROLE_ADMIN, allow_platform_admin=True)
def admin_dashboard(request):
    """Early platform dashboard for administrators."""
    paid_invoices = Invoice.objects.filter(status=Invoice.STATUS_PAID)
    context = get_admin_report_context()
    context.update({
        'tutor_count': User.objects.filter(role=User.ROLE_TUTOR).count(),
        'student_count': User.objects.filter(role=User.ROLE_STUDENT).count(),
        'suspended_count': User.objects.filter(is_suspended=True).count(),
        'paid_revenue': paid_invoices.aggregate(total=Sum('total_amount'))['total'] or 0,
        'pending_revenue': Invoice.objects.filter(status=Invoice.STATUS_PENDING).aggregate(total=Sum('total_amount'))['total'] or 0,
        'paid_invoice_count': paid_invoices.count(),
    })
    return render(request, 'dashboards/admin.html', context)


@role_required(User.ROLE_TUTOR)
def tutor_dashboard(request):
    """Tutor dashboard with classroom and student management entry points."""
    created_credentials = None
    student_form = StudentProvisionForm(tutor=request.user)
    classroom_form = ClassroomForm()

    if request.method == 'POST':
        form_action = request.POST.get('form_action')
        if form_action == 'create_classroom':
            classroom_form = ClassroomForm(request.POST)
            if classroom_form.is_valid():
                create_classroom(tutor=request.user, name=classroom_form.cleaned_data['name'])
                messages.success(request, "Classroom created successfully.")
                return redirect('tutor_dashboard')
        else:
            student_form = StudentProvisionForm(request.POST, tutor=request.user)
            if student_form.is_valid():
                student, temporary_password = create_student_account(
                    tutor=request.user,
                    fullname=student_form.cleaned_data['fullname'],
                    email=student_form.cleaned_data['email'],
                    school_name=student_form.cleaned_data['school_name'],
                    registration_number=student_form.cleaned_data['registration_number'],
                )
                created_credentials = {
                    'name': student.fullname,
                    'email': student.email,
                    'temporary_password': temporary_password,
                    'registration_number': student_form.cleaned_data['registration_number'],
                }
                messages.success(request, "Student account created successfully.")
                student_form = StudentProvisionForm(tutor=request.user)
            else:
                for field_errors in student_form.errors.values():
                    for error in field_errors:
                        messages.error(request, error)

        if classroom_form.errors:
            for field_errors in classroom_form.errors.values():
                for error in field_errors:
                    messages.error(request, error)

    search_form = StudentSearchForm(request.GET)
    search_query = ""
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('q', '')
    students = request.user.provisioned_students.select_related('user').order_by('-created_at')
    if search_query:
        students = students.filter(
            Q(user__fullname__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(registration_number__icontains=search_query)
            | Q(school_name__icontains=search_query)
        )

    classrooms = (
        Classroom.objects.filter(tutor=request.user, is_archived=False)
        .annotate(student_count=Count('students'), exam_count=Count('exams'))
        .order_by('-created_at')
    )
    archived_count = Classroom.objects.filter(tutor=request.user, is_archived=True).count()
    overview = {
        'classroom_count': classrooms.count(),
        'student_count': request.user.provisioned_students.count(),
        'archived_count': archived_count,
    }
    active_subscription = get_active_subscription(tutor=request.user)
    pending_invoice_count = Invoice.objects.filter(tutor=request.user, status=Invoice.STATUS_PENDING).count()
    return render(
        request,
        'dashboards/tutor.html',
        {
            'student_form': student_form,
            'classroom_form': classroom_form,
            'students': students[:25],
            'classrooms': classrooms,
            'overview': overview,
            'search_query': search_query,
            'created_credentials': created_credentials,
            'active_subscription': active_subscription,
            'pending_invoice_count': pending_invoice_count,
        },
    )


@role_required(User.ROLE_TUTOR)
def classroom_detail(request, classroom_id):
    """Show and manage one tutor-owned classroom."""
    classroom = get_object_or_404(Classroom, id=classroom_id, tutor=request.user)
    created_credentials = None
    import_result = None
    student_form = StudentProvisionForm(tutor=request.user)
    bulk_form = BulkStudentImportForm(tutor=request.user, initial={'classroom_id': classroom.id})

    if request.method == 'POST':
        form_action = request.POST.get('form_action')
        if form_action == 'bulk_import':
            bulk_form = BulkStudentImportForm(request.POST, request.FILES, tutor=request.user)
            if bulk_form.is_valid():
                import_result = import_students_from_file(
                    tutor=request.user,
                    upload=bulk_form.cleaned_data['file'],
                    classroom=classroom,
                )
                messages.success(request, f"Imported {len(import_result['created'])} students.")
        else:
            student_form = StudentProvisionForm(request.POST, tutor=request.user)
            if student_form.is_valid():
                student, temporary_password = create_student_account(
                    tutor=request.user,
                    fullname=student_form.cleaned_data['fullname'],
                    email=student_form.cleaned_data['email'],
                    school_name=student_form.cleaned_data['school_name'],
                    registration_number=student_form.cleaned_data['registration_number'],
                )
                assign_student_to_classroom(tutor=request.user, classroom=classroom, student=student)
                created_credentials = {
                    'name': student.fullname,
                    'email': student.email,
                    'temporary_password': temporary_password,
                    'registration_number': student_form.cleaned_data['registration_number'],
                }
                messages.success(request, "Student account created and added to classroom.")
                student_form = StudentProvisionForm(tutor=request.user)
            else:
                for field_errors in student_form.errors.values():
                    for error in field_errors:
                        messages.error(request, error)

        for form in (bulk_form,):
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)

    search_query = request.GET.get('q', '').strip()
    students = StudentProfile.objects.filter(user__joined_rooms=classroom).select_related('user').order_by('user__fullname')
    if search_query:
        students = students.filter(
            Q(user__fullname__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(registration_number__icontains=search_query)
        )
    performance = Submission.objects.filter(exam__classroom=classroom).aggregate(
        submission_count=Count('id'),
        average_score=Avg('score'),
    )
    return render(
        request,
        'dashboards/classroom_detail.html',
        {
            'classroom': classroom,
            'student_form': student_form,
            'bulk_form': bulk_form,
            'students': students,
            'search_query': search_query,
            'performance': performance,
            'created_credentials': created_credentials,
            'import_result': import_result,
        },
    )


@role_required(User.ROLE_TUTOR)
def classroom_edit(request, classroom_id):
    """Edit a tutor-owned classroom name."""
    classroom = get_object_or_404(Classroom, id=classroom_id, tutor=request.user)
    form = ClassroomForm(initial={'name': classroom.name})
    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            update_classroom(tutor=request.user, classroom=classroom, name=form.cleaned_data['name'])
            messages.success(request, "Classroom updated successfully.")
            return redirect('classroom_detail', classroom_id=classroom.id)
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
    return render(request, 'dashboards/classroom_form.html', {'form': form, 'classroom': classroom})


@role_required(User.ROLE_TUTOR)
def classroom_archive(request, classroom_id):
    """Archive a tutor-owned classroom."""
    if request.method == 'POST':
        classroom = get_object_or_404(Classroom, id=classroom_id, tutor=request.user)
        archive_classroom(tutor=request.user, classroom=classroom)
        messages.success(request, "Classroom archived successfully.")
    return redirect('tutor_dashboard')


@role_required(User.ROLE_TUTOR)
def assessment_list(request):
    """List tutor-owned assessments across active classrooms."""
    assessments = (
        Exam.objects.filter(classroom__tutor=request.user)
        .select_related('classroom')
        .annotate(question_count=Count('questions'))
        .order_by('-created_at')
    )
    return render(request, 'dashboards/assessments/list.html', {'assessments': assessments})


@role_required(User.ROLE_TUTOR)
def assessment_create(request):
    """Create a draft assessment for one tutor-owned classroom."""
    classrooms = Classroom.objects.filter(tutor=request.user, is_archived=False).order_by('name')
    form = AssessmentForm(tutor=request.user)
    if request.method == 'POST':
        form = AssessmentForm(request.POST, tutor=request.user)
        if form.is_valid():
            exam = create_assessment(tutor=request.user, data=form.cleaned_data)
            messages.success(request, "Assessment draft created successfully.")
            return redirect('assessment_detail', exam_id=exam.id)
        _push_form_errors(request, form)
    return render(request, 'dashboards/assessments/form.html', {'form': form, 'classrooms': classrooms, 'assessment': None})


@role_required(User.ROLE_TUTOR)
def assessment_edit(request, exam_id):
    """Edit core settings for a tutor-owned assessment."""
    exam = get_object_or_404(Exam, id=exam_id, classroom__tutor=request.user)
    classrooms = Classroom.objects.filter(tutor=request.user, is_archived=False).order_by('name')
    form = AssessmentForm(tutor=request.user, initial=_assessment_initial(exam))
    if request.method == 'POST':
        form = AssessmentForm(request.POST, tutor=request.user)
        if form.is_valid():
            update_assessment(tutor=request.user, exam=exam, data=form.cleaned_data)
            messages.success(request, "Assessment updated successfully.")
            return redirect('assessment_detail', exam_id=exam.id)
        _push_form_errors(request, form)
    return render(request, 'dashboards/assessments/form.html', {'form': form, 'classrooms': classrooms, 'assessment': exam})


@role_required(User.ROLE_TUTOR)
def assessment_detail(request, exam_id):
    """Show assessment builder workspace."""
    exam = get_object_or_404(
        Exam.objects.select_related('classroom').prefetch_related('sections', 'questions__choices'),
        id=exam_id,
        classroom__tutor=request.user,
    )
    section_form = QuestionSectionForm()
    question_form = QuestionForm(exam=exam)
    bulk_form = BulkQuestionImportForm()
    bank_form = BankQuestionSelectForm(tutor=request.user)
    bank_items = QuestionBankItem.objects.filter(tutor=request.user).order_by('-created_at')[:20]
    return render(
        request,
        'dashboards/assessments/detail.html',
        {
            'assessment': exam,
            'section_form': section_form,
            'question_form': question_form,
            'bulk_form': bulk_form,
            'bank_form': bank_form,
            'bank_items': bank_items,
        },
    )


@role_required(User.ROLE_TUTOR)
def assessment_add_section(request, exam_id):
    """Add a section to a tutor-owned assessment."""
    exam = get_object_or_404(Exam, id=exam_id, classroom__tutor=request.user)
    if request.method == 'POST':
        form = QuestionSectionForm(request.POST)
        if form.is_valid():
            create_question_section(tutor=request.user, exam=exam, data=form.cleaned_data)
            messages.success(request, "Section added successfully.")
        else:
            _push_form_errors(request, form)
    return redirect('assessment_detail', exam_id=exam.id)


@role_required(User.ROLE_TUTOR)
def assessment_add_question(request, exam_id):
    """Add one question and its choices to a tutor-owned assessment."""
    exam = get_object_or_404(Exam, id=exam_id, classroom__tutor=request.user)
    if request.method == 'POST':
        form = QuestionForm(request.POST, exam=exam)
        if form.is_valid():
            create_question_from_form(tutor=request.user, exam=exam, data=form.cleaned_data)
            messages.success(request, "Question added successfully.")
        else:
            _push_form_errors(request, form)
    return redirect('assessment_detail', exam_id=exam.id)


@role_required(User.ROLE_TUTOR)
def assessment_import_questions(request, exam_id):
    """Bulk import questions into a tutor-owned assessment."""
    exam = get_object_or_404(Exam, id=exam_id, classroom__tutor=request.user)
    if request.method == 'POST':
        form = BulkQuestionImportForm(request.POST, request.FILES)
        if form.is_valid():
            result = import_questions_from_file(
                tutor=request.user,
                exam=exam,
                upload=form.cleaned_data['file'],
            )
            messages.success(request, f"Imported {len(result['created'])} questions.")
            for error in result['errors']:
                messages.error(request, error)
        else:
            _push_form_errors(request, form)
    return redirect('assessment_detail', exam_id=exam.id)


@role_required(User.ROLE_TUTOR)
def assessment_add_from_bank(request, exam_id):
    """Copy a reusable bank question into a tutor-owned assessment."""
    exam = get_object_or_404(Exam, id=exam_id, classroom__tutor=request.user)
    if request.method == 'POST':
        form = BankQuestionSelectForm(request.POST, tutor=request.user)
        if form.is_valid():
            bank_item = QuestionBankItem.objects.get(id=form.cleaned_data['bank_item_id'], tutor=request.user)
            add_bank_question_to_assessment(tutor=request.user, exam=exam, bank_item=bank_item)
            messages.success(request, "Question added from bank.")
        else:
            _push_form_errors(request, form)
    return redirect('assessment_detail', exam_id=exam.id)


@role_required(User.ROLE_TUTOR)
def assessment_publish(request, exam_id):
    """Publish a tutor-owned assessment after validation."""
    exam = get_object_or_404(Exam, id=exam_id, classroom__tutor=request.user)
    if request.method == 'POST':
        try:
            if not assessment_can_publish_without_invoice(tutor=request.user, exam=exam):
                invoice = get_or_create_assessment_invoice(tutor=request.user, exam=exam)
                messages.info(request, "Complete payment before publishing this assessment.")
                return redirect('invoice_detail', invoice_id=invoice.id)
            publish_assessment(tutor=request.user, exam=exam)
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Assessment published successfully.")
    return redirect('assessment_detail', exam_id=exam.id)


@role_required(User.ROLE_TUTOR)
def tutor_reports(request):
    """Show tutor-wide classroom, assessment, performance, and integrity reports."""
    return render(request, 'reports/tutor_overview.html', get_tutor_report_context(tutor=request.user))


@role_required(User.ROLE_TUTOR)
def classroom_report(request, classroom_id):
    """Show performance analytics for one tutor-owned classroom."""
    classroom = get_object_or_404(Classroom, id=classroom_id, tutor=request.user)
    return render(request, 'reports/classroom_report.html', get_classroom_report_context(tutor=request.user, classroom=classroom))


@role_required(User.ROLE_TUTOR)
def assessment_report(request, exam_id):
    """Show score, question difficulty, completion, and proctoring analytics."""
    exam = get_object_or_404(Exam.objects.select_related('classroom'), id=exam_id, classroom__tutor=request.user)
    return render(request, 'reports/assessment_report.html', get_assessment_report_context(tutor=request.user, exam=exam))


@role_required(User.ROLE_TUTOR)
def assessment_report_export(request, exam_id):
    """Download an Excel-compatible CSV export for an assessment report."""
    exam = get_object_or_404(Exam, id=exam_id, classroom__tutor=request.user)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="assessment-{exam.id}-report.csv"'
    writer = csv.writer(response)
    writer.writerows(tutor_assessment_export_rows(tutor=request.user, exam=exam))
    return response


@role_required(User.ROLE_TUTOR)
def assessment_report_excel_export(request, exam_id):
    """Download a native Excel workbook for an assessment report."""
    exam = get_object_or_404(Exam, id=exam_id, classroom__tutor=request.user)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Assessment Report"
    for row in tutor_assessment_export_rows(tutor=request.user, exam=exam):
        sheet.append([_excel_safe_value(value) for value in row])
    for column_cells in sheet.columns:
        width = max(len(str(cell.value or "")) for cell in column_cells)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(max(width + 2, 12), 42)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(buffer.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="assessment-{exam.id}-report.xlsx"'
    return response


def _excel_safe_value(value):
    """Convert values that Excel cannot store directly."""
    if hasattr(value, "tzinfo") and value.tzinfo:
        return timezone.localtime(value).replace(tzinfo=None)
    return value


@role_required(User.ROLE_TUTOR)
def billing_overview(request):
    """Show tutor invoices and subscription state."""
    invoices = Invoice.objects.filter(tutor=request.user).select_related('assessment', 'subscription_plan')[:30]
    active_subscription = get_active_subscription(tutor=request.user)
    return render(
        request,
        'billing/overview.html',
        {
            'invoices': invoices,
            'active_subscription': active_subscription,
        },
    )


@role_required(User.ROLE_TUTOR)
def subscription_plans(request):
    """List active subscription plans configured by admins."""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price', 'duration_months')
    active_subscription = get_active_subscription(tutor=request.user)
    for plan in plans:
        plan.is_current_plan = bool(active_subscription and active_subscription.plan_id == plan.id)
        plan.upgrade_credit = estimate_subscription_upgrade_credit(tutor=request.user, new_plan=plan)
    return render(
        request,
        'billing/subscription_plans.html',
        {'plans': plans, 'active_subscription': active_subscription},
    )


@role_required(User.ROLE_TUTOR)
def start_subscription(request, plan_id):
    """Create a subscription invoice for the selected plan."""
    plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
    if request.method == 'POST':
        try:
            invoice = create_subscription_invoice(tutor=request.user, plan=plan)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('subscription_plans')
        messages.success(request, "Subscription invoice created.")
        return redirect('invoice_detail', invoice_id=invoice.id)
    return redirect('subscription_plans')


@role_required(User.ROLE_TUTOR)
def invoice_detail(request, invoice_id):
    """Payment page for tutor invoices."""
    invoice = get_object_or_404(
        Invoice.objects.select_related('assessment', 'subscription_plan'),
        id=invoice_id,
        tutor=request.user,
    )
    return render(
        request,
        'billing/invoice_detail.html',
        {
            'invoice': invoice,
            'payments': invoice.payments.order_by('-created_at'),
            'debug_payments_enabled': settings.DEBUG,
        },
    )


@role_required(User.ROLE_TUTOR)
def invoice_start_mpesa(request, invoice_id):
    """Create a local STK payment attempt ready for provider integration."""
    invoice = get_object_or_404(Invoice, id=invoice_id, tutor=request.user)
    if request.method == 'POST' and invoice.status != Invoice.STATUS_PAID:
        phone_number = request.POST.get('phone_number', '').strip()
        payment = create_mpesa_payment_attempt(invoice=invoice, phone_number=phone_number)
        messages.success(
            request,
            f"M-Pesa payment request prepared. Reference payment #{payment.id} when STK Push credentials are connected.",
        )
    return redirect('invoice_detail', invoice_id=invoice.id)


@role_required(User.ROLE_TUTOR)
def invoice_dev_confirm(request, invoice_id):
    """Development-only payment confirmation for local testing."""
    invoice = get_object_or_404(Invoice, id=invoice_id, tutor=request.user)
    if request.method == 'POST' and settings.DEBUG:
        mark_invoice_paid(invoice=invoice, method=Payment.METHOD_MANUAL, provider_reference=f"DEV-{invoice.reference}")
        if invoice.assessment_id:
            try:
                publish_assessment(tutor=request.user, exam=invoice.assessment)
                messages.success(request, "Payment confirmed and assessment published.")
            except ValueError as exc:
                messages.error(request, str(exc))
        else:
            activate_subscription_from_invoice(invoice=invoice)
            messages.success(request, "Payment confirmed and subscription activated.")
    return redirect('invoice_detail', invoice_id=invoice.id)


@csrf_exempt
@require_POST
def mpesa_stk_callback(request):
    """Receive M-Pesa STK callbacks from Daraja."""
    payload = json.loads(request.body.decode("utf-8") or "{}")
    handle_mpesa_stk_callback(payload)
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


@csrf_exempt
@require_POST
def mpesa_c2b_confirmation(request):
    """Receive C2B confirmation payloads for later reconciliation."""
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


@role_required(User.ROLE_TUTOR)
def reset_student_credentials_view(request, student_id):
    """Allow tutors to rotate credentials only for their own students."""
    if request.method != 'POST':
        return redirect('tutor_dashboard')

    try:
        student = User.objects.get(id=student_id, role=User.ROLE_STUDENT)
        temporary_password = reset_student_credentials(tutor=request.user, student=student)
    except (User.DoesNotExist, StudentProfile.DoesNotExist):
        messages.error(request, "Student account was not found.")
    except PermissionError:
        messages.error(request, "You can only reset credentials for your own students.")
    else:
        messages.success(
            request,
            f"New temporary password for {student.fullname}: {temporary_password}",
        )
    return redirect('tutor_dashboard')


def _push_form_errors(request, form):
    """Copy form errors into Django messages for template display."""
    for field_errors in form.errors.values():
        for error in field_errors:
            messages.error(request, error)


def _assessment_initial(exam):
    """Build initial form values from an assessment instance."""
    return {
        'classroom_id': exam.classroom_id,
        'title': exam.title,
        'assessment_type': exam.assessment_type,
        'instructions': exam.instructions,
        'start_time': exam.start_time.strftime('%Y-%m-%dT%H:%M') if exam.start_time else '',
        'end_time': exam.end_time.strftime('%Y-%m-%dT%H:%M') if exam.end_time else '',
        'duration_minutes': exam.duration_minutes,
        'total_marks': exam.total_marks,
        'pass_mark': exam.pass_mark,
        'attempts_allowed': exam.attempts_allowed,
        'back_btn_enabled': exam.back_btn_enabled,
        'allow_late_submission': exam.allow_late_submission,
        'show_results_immediately': exam.show_results_immediately,
        'show_answers': exam.show_answers,
        'randomize_questions': exam.randomize_questions,
        'randomize_choices': exam.randomize_choices,
        'proctoring_enabled': exam.proctoring_enabled,
        'disable_copy_paste': exam.disable_copy_paste,
        'disable_right_click': exam.disable_right_click,
        'disable_text_selection': exam.disable_text_selection,
        'detect_tab_switch': exam.detect_tab_switch,
        'detect_window_blur': exam.detect_window_blur,
        'require_fullscreen': exam.require_fullscreen,
        'detect_fullscreen_exit': exam.detect_fullscreen_exit,
        'detect_refresh': exam.detect_refresh,
        'max_violation_warnings': exam.max_violation_warnings,
        'auto_submit_on_violation': exam.auto_submit_on_violation,
        'auto_disqualify_on_violation': exam.auto_disqualify_on_violation,
    }


@role_required(User.ROLE_STUDENT)
def student_dashboard(request):
    """Show assigned assessments, reminders, todos, and notifications."""
    todo_form = StudentTodoForm(student=request.user)
    if request.method == 'POST':
        form_action = request.POST.get('form_action')
        if form_action == 'create_todo':
            todo_form = StudentTodoForm(request.POST, student=request.user)
            if todo_form.is_valid():
                create_student_todo(student=request.user, data=todo_form.cleaned_data)
                messages.success(request, "Todo added successfully.")
                return redirect('student_dashboard')
            _push_form_errors(request, todo_form)
        elif form_action == 'complete_todo':
            todo = get_object_or_404(StudentTodo, id=request.POST.get('todo_id'), student=request.user)
            complete_student_todo(student=request.user, todo=todo)
            messages.success(request, "Todo completed.")
            return redirect('student_dashboard')
        elif form_action == 'mark_notification_read':
            notification = get_object_or_404(StudentNotification, id=request.POST.get('notification_id'), student=request.user)
            mark_student_notification_read(student=request.user, notification=notification)
            return redirect('student_dashboard')

    context = get_student_dashboard_context(student=request.user)
    context['todo_form'] = todo_form
    return render(request, 'dashboards/student.html', context)


@role_required(User.ROLE_STUDENT)
def student_reports(request):
    """Show the signed-in student's assessment progress and released results."""
    return render(request, 'reports/student_report.html', get_student_report_context(student=request.user))


@role_required(User.ROLE_STUDENT)
def student_assessment_start(request, exam_id):
    """Start or resume a student's assigned assessment attempt."""
    try:
        exam = get_student_assessment_for_taking(student=request.user, exam_id=exam_id)
        submission = get_or_start_submission(student=request.user, exam=exam)
    except Exam.DoesNotExist:
        messages.error(request, "Assessment was not found.")
        return redirect('student_dashboard')
    except (PermissionError, ValueError) as exc:
        messages.error(request, str(exc))
        return redirect('student_dashboard')

    if submission.completed:
        return redirect('student_assessment_result', submission_id=submission.id)
    return redirect('student_assessment_take', submission_id=submission.id)


@role_required(User.ROLE_STUDENT)
def student_assessment_take(request, submission_id):
    """Render and process a mobile-first assessment attempt."""
    submission = get_object_or_404(
        Submission.objects.select_related('exam', 'exam__classroom'),
        id=submission_id,
        student=request.user,
    )
    if submission.completed:
        return redirect('student_assessment_result', submission_id=submission.id)

    if request.method == 'POST':
        answer_data = _answers_from_request(request)
        action = request.POST.get('form_action')
        try:
            if action == 'save':
                save_submission_answers(submission=submission, answer_data=answer_data)
                messages.success(request, "Answers saved.")
                return redirect('student_assessment_take', submission_id=submission.id)
            submitted = submit_assessment_attempt(
                student=request.user,
                submission=submission,
                answer_data=answer_data,
            )
            messages.success(request, "Assessment submitted successfully.")
            return redirect('student_assessment_result', submission_id=submitted.id)
        except ValueError as exc:
            if "Time is up" in str(exc):
                submitted = submit_assessment_attempt(
                    student=request.user,
                    submission=submission,
                    answer_data=None,
                    auto_submitted=True,
                )
                messages.error(request, "Time is up. Your saved answers were submitted.")
                return redirect('student_assessment_result', submission_id=submitted.id)
            messages.error(request, str(exc))

    context = build_attempt_context(submission=submission)
    if context['time_remaining_seconds'] == 0:
        submitted = submit_assessment_attempt(
            student=request.user,
            submission=submission,
            answer_data=None,
            auto_submitted=True,
        )
        messages.error(request, "Time is up. Your saved answers were submitted.")
        return redirect('student_assessment_result', submission_id=submitted.id)
    return render(request, 'student/assessment_take.html', context)


@role_required(User.ROLE_STUDENT)
def student_assessment_result(request, submission_id):
    """Show a completed attempt summary respecting tutor visibility settings."""
    submission = get_object_or_404(
        Submission.objects.select_related('exam', 'exam__classroom').prefetch_related('answers__question'),
        id=submission_id,
        student=request.user,
        completed=True,
    )
    return render(request, 'student/assessment_result.html', {'submission': submission})


@role_required(User.ROLE_STUDENT)
@require_POST
def student_proctor_violation(request, submission_id):
    """Receive browser-side proctoring violations for a live attempt."""
    submission = get_object_or_404(
        Submission.objects.select_related('exam'),
        id=submission_id,
        student=request.user,
    )
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}
    violation_type = payload.get("violation_type", "")
    allowed_types = dict(ProctorLog.VIOLATION_TYPES)
    if violation_type not in allowed_types:
        return JsonResponse({"error": "Invalid violation type."}, status=400)
    _, action = record_proctor_violation(
        student=request.user,
        submission=submission,
        violation_type=violation_type,
        details=payload.get("details", ""),
    )
    action["result_url"] = reverse("student_assessment_result", args=[submission.id]) if action.get("disqualified") or action.get("submitted") else ""
    return JsonResponse(action)


def _answers_from_request(request):
    """Extract posted assessment answers keyed by question id."""
    answers = {}
    for key in request.POST:
        if not key.startswith("answer_"):
            continue
        question_id = key.replace("answer_", "", 1)
        values = request.POST.getlist(key)
        answers[question_id] = values if len(values) > 1 else values[0]
    return answers
