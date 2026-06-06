import csv
from io import TextIOWrapper

from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from openpyxl import load_workbook

from .models import Classroom, StudentProfile, TutorProfile, User


def build_unique_username(email):
    """Create a stable unique username from an email address."""
    UserModel = get_user_model()
    base_username = email.split("@", 1)[0].lower()[:140] or "user"
    username = base_username
    counter = 1
    while UserModel.objects.filter(username=username).exists():
        counter += 1
        suffix = f"-{counter}"
        username = f"{base_username[:150 - len(suffix)]}{suffix}"
    return username


def create_tutor_account(*, fullname, email, password, phone_number="", institution_name=""):
    """Create a self-registered tutor and matching tutor profile."""
    user = User.objects.create_user(
        username=build_unique_username(email),
        email=email,
        password=password,
        fullname=fullname,
        phone_number=phone_number,
        role=User.ROLE_TUTOR,
    )
    TutorProfile.objects.create(user=user, institution_name=institution_name)
    return user


def create_student_account(*, tutor, fullname, email, school_name, registration_number):
    """Provision a student account owned by a tutor.

    The generated password is returned once so the tutor can share it. Students
    may also log in using their registration number during the early workflow.
    """
    temporary_password = get_random_string(10)
    user = User.objects.create_user(
        username=build_unique_username(email),
        email=email,
        password=temporary_password,
        fullname=fullname,
        role=User.ROLE_STUDENT,
        school_name=school_name,
        registration_id=registration_number,
    )
    StudentProfile.objects.create(
        user=user,
        tutor=tutor,
        school_name=school_name,
        registration_number=registration_number,
    )
    return user, temporary_password


def generate_classroom_code():
    """Create a short join/reference code for a classroom."""
    code = get_random_string(8).upper()
    while Classroom.objects.filter(room_id=code).exists():
        code = get_random_string(8).upper()
    return code


def create_classroom(*, tutor, name):
    """Create a tutor-owned classroom with a non-public legacy password value."""
    return Classroom.objects.create(
        tutor=tutor,
        name=name,
        room_id=generate_classroom_code(),
        password=get_random_string(12),
    )


def update_classroom(*, tutor, classroom, name):
    """Update a tutor-owned classroom."""
    if classroom.tutor_id != tutor.id:
        raise PermissionError("Classroom is not owned by this tutor.")
    classroom.name = name
    classroom.save(update_fields=["name", "updated_at"])
    return classroom


def archive_classroom(*, tutor, classroom):
    """Archive a tutor-owned classroom without deleting history."""
    if classroom.tutor_id != tutor.id:
        raise PermissionError("Classroom is not owned by this tutor.")
    classroom.is_archived = True
    classroom.save(update_fields=["is_archived", "updated_at"])
    return classroom


def assign_student_to_classroom(*, tutor, classroom, student):
    """Attach a tutor-owned student to a tutor-owned classroom."""
    if classroom.tutor_id != tutor.id:
        raise PermissionError("Classroom is not owned by this tutor.")
    if not StudentProfile.objects.filter(tutor=tutor, user=student).exists():
        raise PermissionError("Student is not owned by this tutor.")
    classroom.students.add(student)
    return classroom


def reset_student_credentials(*, tutor, student):
    """Reset a tutor-owned student's temporary password.

    Ownership is checked here so views and future APIs use the same guardrail.
    """
    try:
        profile = StudentProfile.objects.select_related("user").get(user=student, tutor=tutor)
    except StudentProfile.DoesNotExist as exc:
        raise PermissionError("Student is not owned by this tutor.") from exc
    temporary_password = get_random_string(10)
    profile.user.set_password(temporary_password)
    profile.user.save(update_fields=["password"])
    profile.must_change_password = True
    profile.save(update_fields=["must_change_password"])
    return temporary_password


def import_students_from_file(*, tutor, upload, classroom=None):
    """Provision students from CSV/XLSX rows and optionally assign a classroom.

    Expected columns are `fullname`, `email`, `school_name`, and
    `registration_number`. The result carries created credentials so tutors can
    share them immediately after import.
    """
    rows = _read_student_rows(upload)
    result = {"created": [], "skipped": [], "errors": []}

    for row_number, row in enumerate(rows, start=2):
        fullname = (row.get("fullname") or "").strip()
        email = (row.get("email") or "").strip().lower()
        school_name = (row.get("school_name") or "").strip()
        registration_number = (row.get("registration_number") or "").strip()

        if not all([fullname, email, school_name, registration_number]):
            result["errors"].append(f"Row {row_number}: missing required data.")
            continue
        if User.objects.filter(email=email).exists():
            result["skipped"].append(f"Row {row_number}: {email} already exists.")
            continue
        if StudentProfile.objects.filter(tutor=tutor, registration_number=registration_number).exists():
            result["skipped"].append(f"Row {row_number}: registration {registration_number} already exists.")
            continue

        student, temporary_password = create_student_account(
            tutor=tutor,
            fullname=fullname,
            email=email,
            school_name=school_name,
            registration_number=registration_number,
        )
        if classroom:
            assign_student_to_classroom(tutor=tutor, classroom=classroom, student=student)
        result["created"].append(
            {
                "name": student.fullname,
                "email": student.email,
                "registration_number": registration_number,
                "temporary_password": temporary_password,
            }
        )

    return result


def _read_student_rows(upload):
    """Read normalized dict rows from a CSV or XLSX upload."""
    name = upload.name.lower()
    upload.seek(0)
    if name.endswith(".csv"):
        wrapper = TextIOWrapper(upload.file, encoding="utf-8-sig")
        return list(csv.DictReader(wrapper))

    workbook = load_workbook(upload, read_only=True, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(value).strip().lower() if value is not None else "" for value in rows[0]]
    normalized = []
    for values in rows[1:]:
        normalized.append(
            {
                headers[index]: "" if value is None else str(value)
                for index, value in enumerate(values)
                if index < len(headers)
            }
        )
    return normalized
