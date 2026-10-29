from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin


class DashboardAccessMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Logged in + is_staff + the view's Django permission (superusers pass all)."""
    permission_required = ()
    section = ""        # highlights the sidebar link
    page_title = ""

    def has_permission(self):
        user = self.request.user
        return user.is_active and user.is_staff and super().has_permission()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["section"] = self.section
        ctx["page_title"] = self.page_title
        return ctx