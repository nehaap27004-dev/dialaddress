from .models import Profile


class ProfileMiddleware:
    """Attaches request.profile for logged-in users (creates one for older accounts)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.profile = None
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            request.profile, _ = Profile.objects.get_or_create(user=user)
        return self.get_response(request)