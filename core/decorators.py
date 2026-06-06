from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*allowed_roles, allow_platform_admin=False):
    """Require login and one of the listed roles before entering a view."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            user = request.user
            if allow_platform_admin and user.is_platform_admin:
                return view_func(request, *args, **kwargs)
            if user.role in allowed_roles and not user.is_suspended:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have permission to access that page.")
            return redirect("dashboard")

        return wrapped

    return decorator
