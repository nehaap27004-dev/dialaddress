from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    """Lets people log in with either their username or their email."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if not username or password is None:
            return None

        candidates = User.objects.filter(
            Q(username__iexact=username) | Q(email__iexact=username)
        )
        for user in candidates:
            if user.check_password(password):
                # Blocked users are returned on purpose, so the login form
                # can tell them they are blocked instead of "wrong password".
                return user

        User().set_password(password)  # keeps response time similar
        return None