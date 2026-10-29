from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from directory.models import Business, Category, CategoryGroup, Profile

from .forms import (BusinessManageForm, CategoryForm, CategoryGroupForm, UserManageForm)
from .mixins import DashboardAccessMixin
from directory.models import (Business, Category, CategoryGroup, City, Country,
                              Feature, Profile, Review)

from .forms import (BusinessManageForm, CategoryForm, CategoryGroupForm, CityForm,
                    CountryForm, FeatureForm, ReviewManageForm, UserManageForm)
User = get_user_model()
PAGE_SIZE = 20


def safe_next(request, default_name):
    nxt = request.POST.get("next", "")
    ok = url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()},
                                         require_https=request.is_secure())
    return nxt if ok else reverse(default_name)


# ---------- generic bases ----------
class ListBase(DashboardAccessMixin, ListView):
    paginate_by = PAGE_SIZE

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx


class AddView(DashboardAccessMixin, SuccessMessageMixin, CreateView):
    template_name = "dashboard/form.html"


class EditView(DashboardAccessMixin, SuccessMessageMixin, UpdateView):
    template_name = "dashboard/form.html"


class RemoveView(DashboardAccessMixin, DeleteView):
    template_name = "dashboard/confirm_delete.html"

    def form_valid(self, form):
        messages.success(self.request, f"“{self.object}” was deleted.")
        return super().form_valid(form)


# ---------- home ----------
class HomeView(DashboardAccessMixin, TemplateView):
    template_name = "dashboard/home.html"
    section, page_title = "home", "Dashboard"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["biz"] = Business.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(is_active=False)),
            featured=Count("id", filter=Q(is_featured=True)),
        )
        ctx["usr"] = Profile.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=Profile.Status.PENDING)),
            blocked=Count("id", filter=Q(status=Profile.Status.BLOCKED)),
        )
        ctx["category_count"] = Category.objects.count()
        ctx["recent_pending"] = (Business.objects.filter(is_active=False)
                                 .select_related("category", "city", "owner")
                                 .order_by("-created_at")[:8])
        return ctx


# ---------- businesses ----------
class BusinessListView(ListBase):
    model = Business
    permission_required = "directory.view_business"
    template_name = "dashboard/business_list.html"
    section, page_title = "businesses", "Businesses"

    def get_queryset(self):
        qs = (Business.objects.select_related("category", "subcategory", "city", "owner")
              .order_by("-created_at"))
        g = self.request.GET
        q = g.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q)
                           | Q(city__name__icontains=q) | Q(owner__username__icontains=q))
        status = g.get("status", "")
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "pending":
            qs = qs.filter(is_active=False)
        elif status == "featured":
            qs = qs.filter(is_featured=True)
        if g.get("category", "").isdigit():
            qs = qs.filter(category_id=g["category"])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.request.GET
        ctx.update(q=g.get("q", ""), status=g.get("status", ""), category=g.get("category", ""),
                   categories=Category.objects.filter(parent__isnull=True))
        return ctx


class BusinessAddView(AddView):
    model = Business
    form_class = BusinessManageForm
    permission_required = "directory.add_business"
    template_name = "dashboard/business_form.html"
    success_url = reverse_lazy("dashboard:business_list")
    success_message = "“%(name)s” was added."
    section, page_title = "businesses", "Add business"


class BusinessEditView(EditView):
    model = Business
    form_class = BusinessManageForm
    permission_required = "directory.change_business"
    template_name = "dashboard/business_form.html"
    success_url = reverse_lazy("dashboard:business_list")
    success_message = "“%(name)s” was saved."
    section, page_title = "businesses", "Edit business"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        b = self.object
        ctx["extra_links"] = [
            ("Opening hours", reverse("manage_hours", args=[b.slug])),
            ("Photos", reverse("manage_photos", args=[b.slug])),
            ("View on site", reverse("business_detail", args=[b.slug])),
        ]
        return ctx


class BusinessDeleteView(RemoveView):
    model = Business
    permission_required = "directory.delete_business"
    success_url = reverse_lazy("dashboard:business_list")
    section, page_title = "businesses", "Delete business"

    def form_valid(self, form):
        b = self.object
        # uploaded files are not removed by Django when the row is deleted
        files = [p.image for p in b.photos.all()] + [f for f in (b.logo, b.cover_image) if f]
        response = super().form_valid(form)
        for f in files:
            f.delete(save=False)
        return response


class BusinessActionView(DashboardAccessMixin, View):
    """Bulk actions on the ticked rows of the business list."""
    permission_required = "directory.change_business"
    ACTIONS = {
        "approve": {"is_active": True},
        "hide": {"is_active": False},
        "feature": {"is_featured": True},
        "unfeature": {"is_featured": False},
        "verify": {"is_verified": True},
        "unverify": {"is_verified": False},
    }

    def post(self, request):
        action = request.POST.get("action")
        ids = [int(i) for i in request.POST.getlist("ids") if i.isdigit()]
        if action not in self.ACTIONS or not ids:
            messages.error(request, "Tick at least one business and choose an action.")
        else:
            n = (Business.objects.filter(pk__in=ids)
                 .update(updated_at=timezone.now(), **self.ACTIONS[action]))
            messages.success(request, f"{n} business(es) updated.")
        return redirect(safe_next(request, "dashboard:business_list"))


class SubcategoryOptionsView(DashboardAccessMixin, View):
    """Feeds the Subcategory dropdown on the business form."""
    def get(self, request):
        cid = request.GET.get("category", "")
        rows = Category.objects.filter(parent_id=cid).values("id", "name") if cid.isdigit() else []
        return JsonResponse({"results": list(rows)})


# ---------- categories ----------
class CategoryListView(ListBase):
    model = Category
    permission_required = "directory.view_category"
    template_name = "dashboard/category_list.html"
    paginate_by = 50
    section, page_title = "categories", "Categories"

    def get_queryset(self):
        counts = dict(main_count=Count("businesses", distinct=True),
                      sub_count=Count("sub_businesses", distinct=True))
        children = Category.objects.annotate(**counts).order_by("order", "name")
        qs = (Category.objects.filter(parent__isnull=True).select_related("group")
              .annotate(**counts).prefetch_related(Prefetch("children", queryset=children)))
        if self.request.GET.get("group", "").isdigit():
            qs = qs.filter(group_id=self.request.GET["group"])
        return qs.order_by("order", "name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["groups"] = CategoryGroup.objects.all()
        ctx["group"] = self.request.GET.get("group", "")
        return ctx


class CategoryAddView(AddView):
    model = Category
    form_class = CategoryForm
    permission_required = "directory.add_category"
    success_url = reverse_lazy("dashboard:category_list")
    success_message = "“%(name)s” was added."
    section, page_title = "categories", "Add category"


class CategoryEditView(EditView):
    model = Category
    form_class = CategoryForm
    permission_required = "directory.change_category"
    success_url = reverse_lazy("dashboard:category_list")
    success_message = "“%(name)s” was saved."
    section, page_title = "categories", "Edit category"


class CategoryDeleteView(RemoveView):
    model = Category
    permission_required = "directory.delete_category"
    success_url = reverse_lazy("dashboard:category_list")
    section, page_title = "categories", "Delete category"

    def form_valid(self, form):
        c = self.object
        # Business.category is CASCADE: deleting a used category would delete its businesses
        if c.businesses.exists() or c.sub_businesses.exists() or c.children.exists():
            messages.error(self.request, "This category still has businesses or subcategories. "
                                         "Move or delete them first.")
            return redirect("dashboard:category_list")
        return super().form_valid(form)


# ---------- category groups ----------
class GroupListView(ListBase):
    model = CategoryGroup
    permission_required = "directory.view_categorygroup"
    template_name = "dashboard/group_list.html"
    section, page_title = "groups", "Category groups"

    def get_queryset(self):
        return CategoryGroup.objects.annotate(n=Count("categories")).order_by("order", "name")

class GroupAddView(AddView):
    model = CategoryGroup
    form_class = CategoryGroupForm
    permission_required = "directory.add_categorygroup"
    success_url = reverse_lazy("dashboard:group_list")
    success_message = "“%(name)s” was added."
    section, page_title = "groups", "Add category group"


class GroupEditView(EditView):
    model = CategoryGroup
    form_class = CategoryGroupForm
    permission_required = "directory.change_categorygroup"
    success_url = reverse_lazy("dashboard:group_list")
    success_message = "“%(name)s” was saved."
    section, page_title = "groups", "Edit category group"


class GroupDeleteView(RemoveView):
    model = CategoryGroup
    permission_required = "directory.delete_categorygroup"
    success_url = reverse_lazy("dashboard:group_list")
    section, page_title = "groups", "Delete category group"


# ---------- users ----------
class UserListView(ListBase):
    model = User
    permission_required = "auth.view_user"
    template_name = "dashboard/user_list.html"
    section, page_title = "users", "Users"

    def get_queryset(self):
        qs = (User.objects.select_related("profile")
              .annotate(biz_count=Count("businesses")).order_by("-date_joined"))
        g = self.request.GET
        q = g.get("q", "").strip()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q))
        if g.get("status") in ("pending", "approved", "blocked"):
            qs = qs.filter(profile__status=g["status"])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(q=self.request.GET.get("q", ""), status=self.request.GET.get("status", ""))
        return ctx


class UserEditView(EditView):
    model = User
    form_class = UserManageForm
    permission_required = "auth.change_user"
    success_url = reverse_lazy("dashboard:user_list")
    success_message = "User updated."
    section, page_title = "users", "Edit user"

    def get_queryset(self):
        qs = User.objects.all()
        return qs if self.request.user.is_superuser else qs.filter(is_superuser=False)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["acting_user"] = self.request.user
        return kwargs


class UserActionView(DashboardAccessMixin, View):
    permission_required = "auth.change_user"
    STATUS = {"approve": Profile.Status.APPROVED,
              "block": Profile.Status.BLOCKED,
              "unblock": Profile.Status.APPROVED}

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        action = request.POST.get("action")
        if action not in self.STATUS:
            messages.error(request, "Unknown action.")
        elif target.pk == request.user.pk or target.is_superuser:
            messages.error(request, "You can't change this account.")
        else:
            profile, _ = Profile.objects.get_or_create(user=target)
            profile.set_status(self.STATUS[action], by=request.user,
                               reason=request.POST.get("reason", "")[:255])
            note = " Their listings were hidden." if action == "block" else ""
            messages.success(request, f"{target.username}: {action} done.{note}")
        return redirect(safe_next(request, "dashboard:user_list"))

# ---------- countries ----------
class CountryListView(ListBase):
    model = Country
    permission_required = "directory.view_country"
    template_name = "dashboard/country_list.html"
    section, page_title = "countries", "Countries"

    def get_queryset(self):
        return Country.objects.annotate(n=Count("cities")).order_by("name")


class CountryAddView(AddView):
    model = Country
    form_class = CountryForm
    permission_required = "directory.add_country"
    success_url = reverse_lazy("dashboard:country_list")
    success_message = "“%(name)s” was added."
    section, page_title = "countries", "Add country"


class CountryEditView(EditView):
    model = Country
    form_class = CountryForm
    permission_required = "directory.change_country"
    success_url = reverse_lazy("dashboard:country_list")
    success_message = "“%(name)s” was saved."
    section, page_title = "countries", "Edit country"


class CountryDeleteView(RemoveView):
    model = Country
    permission_required = "directory.delete_country"
    success_url = reverse_lazy("dashboard:country_list")
    section, page_title = "countries", "Delete country"

    def form_valid(self, form):
        if self.object.cities.exists():
            messages.error(self.request, "This country still has cities. Delete or move them first.")
            return redirect("dashboard:country_list")
        return super().form_valid(form)


# ---------- cities ----------
class CityListView(ListBase):
    model = City
    permission_required = "directory.view_city"
    template_name = "dashboard/city_list.html"
    section, page_title = "cities", "Cities"

    def get_queryset(self):
        qs = City.objects.select_related("country").annotate(n=Count("businesses"))
        g = self.request.GET
        q = g.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(state__icontains=q))
        if g.get("country", "").isdigit():
            qs = qs.filter(country_id=g["country"])
        return qs.order_by("country__name", "name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(q=self.request.GET.get("q", ""), country=self.request.GET.get("country", ""),
                   countries=Country.objects.order_by("name"))
        return ctx


class CityAddView(AddView):
    model = City
    form_class = CityForm
    permission_required = "directory.add_city"
    success_url = reverse_lazy("dashboard:city_list")
    success_message = "“%(name)s” was added."
    section, page_title = "cities", "Add city"


class CityEditView(EditView):
    model = City
    form_class = CityForm
    permission_required = "directory.change_city"
    success_url = reverse_lazy("dashboard:city_list")
    success_message = "“%(name)s” was saved."
    section, page_title = "cities", "Edit city"


class CityDeleteView(RemoveView):
    model = City
    permission_required = "directory.delete_city"
    success_url = reverse_lazy("dashboard:city_list")
    section, page_title = "cities", "Delete city"

    def form_valid(self, form):
        # Business.city is CASCADE: deleting a used city would delete its businesses
        if self.object.businesses.exists():
            messages.error(self.request, "This city still has businesses. Move or delete them first.")
            return redirect("dashboard:city_list")
        return super().form_valid(form)


# ---------- features ----------
class FeatureListView(ListBase):
    model = Feature
    permission_required = "directory.view_feature"
    template_name = "dashboard/feature_list.html"
    section, page_title = "features", "Features"

    def get_queryset(self):
        return Feature.objects.annotate(n=Count("businesses")).order_by("name")


class FeatureAddView(AddView):
    model = Feature
    form_class = FeatureForm
    permission_required = "directory.add_feature"
    success_url = reverse_lazy("dashboard:feature_list")
    success_message = "“%(name)s” was added."
    section, page_title = "features", "Add feature"


class FeatureEditView(EditView):
    model = Feature
    form_class = FeatureForm
    permission_required = "directory.change_feature"
    success_url = reverse_lazy("dashboard:feature_list")
    success_message = "“%(name)s” was saved."
    section, page_title = "features", "Edit feature"


class FeatureDeleteView(RemoveView):
    model = Feature
    permission_required = "directory.delete_feature"
    success_url = reverse_lazy("dashboard:feature_list")
    section, page_title = "features", "Delete feature"


# ---------- reviews ----------
class ReviewListView(ListBase):
    model = Review
    permission_required = "directory.view_review"
    template_name = "dashboard/review_list.html"
    section, page_title = "reviews", "Reviews"

    def get_queryset(self):
        qs = Review.objects.select_related("business")
        g = self.request.GET
        q = g.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(comment__icontains=q)
                           | Q(business__name__icontains=q))
        if g.get("status") == "visible":
            qs = qs.filter(is_approved=True)
        elif g.get("status") == "hidden":
            qs = qs.filter(is_approved=False)
        if g.get("rating", "") in ("1", "2", "3", "4", "5"):
            qs = qs.filter(rating=g["rating"])
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        g = self.request.GET
        ctx.update(q=g.get("q", ""), status=g.get("status", ""), rating=g.get("rating", ""))
        return ctx


class ReviewEditView(EditView):
    model = Review
    form_class = ReviewManageForm
    permission_required = "directory.change_review"
    success_url = reverse_lazy("dashboard:review_list")
    success_message = "Review saved."
    section, page_title = "reviews", "Edit review"


class ReviewDeleteView(RemoveView):
    model = Review
    permission_required = "directory.delete_review"
    success_url = reverse_lazy("dashboard:review_list")
    section, page_title = "reviews", "Delete review"


class ReviewActionView(DashboardAccessMixin, View):
    """Bulk approve / hide / delete on the ticked rows of the review list."""
    permission_required = "directory.change_review"

    def post(self, request):
        action = request.POST.get("action")
        ids = [int(i) for i in request.POST.getlist("ids") if i.isdigit()]
        if action not in ("approve", "hide", "delete") or not ids:
            messages.error(request, "Tick at least one review and choose an action.")
        elif action == "delete" and not request.user.has_perm("directory.delete_review"):
            messages.error(request, "You don't have permission to delete reviews.")
        else:
            reviews = Review.objects.filter(pk__in=ids)
            business_ids = list(reviews.values_list("business_id", flat=True).distinct())
            n = reviews.count()
            if action == "delete":
                reviews.delete()  # the signal refreshes each rating
            else:
                reviews.update(is_approved=(action == "approve"))
                # update() skips signals, so recalculate the ratings here
                for b in Business.objects.filter(pk__in=business_ids):
                    b.refresh_rating()
            messages.success(request, f"{n} review(s) updated.")
        return redirect(safe_next(request, "dashboard:review_list"))