from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def approved_required(view):
    """Pending accounts can browse, but can't add or edit listings."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        profile = getattr(request, "profile", None)
        if profile and profile.status == "pending":
            messages.info(
                request,
                "Your account is waiting for approval. You can add a business once it is approved.",
            )
            return redirect("home")
        return view(request, *args, **kwargs)

    return wrapper