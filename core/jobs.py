from datetime import timedelta

from django.core.mail import send_mail
from django.db.models import Count
from django.utils import timezone

from .models import BackgroundTaskLog, Invoice, Payment, StudentNotification, StudentReminder
from .services import get_assessment_report_context
from .tasking import registered_task


@registered_task("notifications.send_email")
def send_email_notification(*, subject, message, recipient_list):
    """Send a plain email notification."""
    delivered = send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=recipient_list,
        fail_silently=False,
    )
    return {"delivered": delivered, "recipients": len(recipient_list)}


@registered_task("reminders.dispatch_due")
def dispatch_due_reminders(*, limit=100):
    """Create notifications and email messages for due student reminders."""
    now = timezone.now()
    reminders = (
        StudentReminder.objects.filter(is_sent=False, remind_at__lte=now)
        .select_related("student", "assessment", "todo")
        .order_by("remind_at")[:limit]
    )
    sent_count = 0
    for reminder in reminders:
        StudentNotification.objects.create(
            student=reminder.student,
            assessment=reminder.assessment,
            title=reminder.title,
            message=_reminder_message(reminder),
            notification_type=StudentNotification.TYPE_REMINDER,
        )
        if reminder.student.email:
            send_mail(
                subject=reminder.title,
                message=_reminder_message(reminder),
                from_email=None,
                recipient_list=[reminder.student.email],
                fail_silently=True,
            )
        reminder.is_sent = True
        reminder.sent_at = now
        reminder.save(update_fields=["is_sent", "sent_at"])
        sent_count += 1
    return {"sent": sent_count}


@registered_task("payments.fail_stale_pending")
def fail_stale_pending_payments(*, older_than_minutes=60):
    """Mark old pending payment attempts failed so tutors can retry cleanly."""
    cutoff = timezone.now() - timedelta(minutes=older_than_minutes)
    payments = Payment.objects.filter(status=Payment.STATUS_PENDING, created_at__lte=cutoff).select_related("invoice")
    failed_count = 0
    invoice_ids = set()
    for payment in payments:
        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=["status"])
        failed_count += 1
        invoice_ids.add(payment.invoice_id)
    invoice_count = 0
    for invoice in Invoice.objects.filter(id__in=invoice_ids, status=Invoice.STATUS_PENDING):
        if not invoice.payments.filter(status=Payment.STATUS_SUCCESSFUL).exists():
            invoice.status = Invoice.STATUS_FAILED
            invoice.save(update_fields=["status"])
            invoice_count += 1
    return {"failed_payments": failed_count, "failed_invoices": invoice_count}


@registered_task("reports.assessment_snapshot")
def generate_assessment_report_snapshot(*, tutor_id, exam_id):
    """Generate a compact assessment report summary for async execution."""
    from .models import Exam, User

    tutor = User.objects.get(id=tutor_id)
    exam = Exam.objects.select_related("classroom").get(id=exam_id)
    context = get_assessment_report_context(tutor=tutor, exam=exam)
    return {
        "assessment": context["assessment"].title,
        "completed_count": context["summary"]["completed_count"],
        "completion_rate": context["summary"]["completion_rate"],
        "average_score": float(context["summary"]["average_score"] or 0),
        "violation_count": context["summary"]["violation_count"],
        "question_count": len(context["question_rows"]),
    }


@registered_task("cleanup.old_task_logs")
def cleanup_old_task_logs(*, older_than_days=30):
    """Delete old successful/failed task logs."""
    cutoff = timezone.now() - timedelta(days=older_than_days)
    deleted, _ = BackgroundTaskLog.objects.filter(created_at__lt=cutoff).delete()
    return {"deleted": deleted}


@registered_task("cleanup.old_read_notifications")
def cleanup_old_read_notifications(*, older_than_days=90):
    """Delete old read student notifications."""
    cutoff = timezone.now() - timedelta(days=older_than_days)
    deleted, _ = StudentNotification.objects.filter(is_read=True, read_at__lt=cutoff).delete()
    return {"deleted": deleted}


def _reminder_message(reminder):
    if reminder.assessment:
        return f"Reminder for {reminder.assessment.title}."
    if reminder.todo:
        return f"Reminder for todo: {reminder.todo.title}."
    return reminder.title


def queued_task_counts():
    """Return task status totals for admin observability."""
    return {
        row["status"]: row["count"]
        for row in BackgroundTaskLog.objects.values("status").annotate(count=Count("id"))
    }
