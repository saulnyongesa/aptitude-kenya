from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.db.models import Avg, Count, Q
from .forms import BulkStudentImportForm, ClassroomForm, LoginForm, StudentProvisionForm, StudentSearchForm, TutorRegistrationForm
from .models import Classroom, SiteStatistic, ContactMessage, StudentProfile, Submission, User
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from .decorators import role_required
from .services import archive_classroom, assign_student_to_classroom, create_classroom, create_student_account, create_tutor_account, import_students_from_file, reset_student_credentials, update_classroom

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
    context = {
        'tutor_count': User.objects.filter(role=User.ROLE_TUTOR).count(),
        'student_count': User.objects.filter(role=User.ROLE_STUDENT).count(),
        'suspended_count': User.objects.filter(is_suspended=True).count(),
    }
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


@role_required(User.ROLE_STUDENT)
def student_dashboard(request):
    """Early student dashboard showing provisioned identity details."""
    return render(request, 'dashboards/student.html')
