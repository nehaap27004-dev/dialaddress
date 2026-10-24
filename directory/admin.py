from datetime import time

from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.sessions.models import Session
from django.db.models import Count
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Business, BusinessPhoto, Category, City, Country,
    Feature, OpeningHour, Profile, Review,
)
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug", "icon", "has_content")
    list_filter = ("parent",)
    search_fields = ("name",)
    fieldsets = (
        (None, {"fields": ("name", "slug", "icon", "parent")}),
        ("'More' panel on the search page", {
            "description": "Shown when visitors click More at the end of a category's results. The button appears only if the description is filled in.",
            "fields": ("info_heading", "info_subheading", "info_content"),
        }),
    )

    @admin.display(description="Panel text", boolean=True)
    def has_content(self, obj):
        return obj.has_info

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "slug")
    search_fields = ("name", "code")


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "state", "country", "slug")
    search_fields = ("name", "state")
    list_filter = ("country", "state")


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")


class PhotoInline(admin.TabularInline):
    model = BusinessPhoto
    extra = 3


class HourInline(admin.TabularInline):
    model = OpeningHour
    extra = 0
    max_num = 7


class BusinessAdminForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = "__all__"
        widgets = {
            "logo_bg_color": forms.TextInput(attrs={
                "type": "color",
                "style": "width:70px;height:38px;padding:2px;cursor:pointer;",
            }),
        }

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    form = BusinessAdminForm
    list_display = (
        "name", "category", "city", "owner", "rating",
        "is_verified", "is_featured", "is_active",
    )
    list_filter = ("category", "city", "is_verified", "is_featured", "is_active")
    search_fields = ("name", "address", "phone")
    list_editable = ("is_verified", "is_featured", "is_active")
    filter_horizontal = ("features",)
    raw_id_fields = ("owner",)
    readonly_fields = ("logo_preview",)
    inlines = [HourInline, PhotoInline]
    form = BusinessAdminForm
    readonly_fields = ("logo_preview",)   # add "cover_preview" here too if you use it

    class Media:
        js = ("directory/js/logo_color.js",)
    actions = ["set_default_hours", "approve_selected"]

    fieldsets = (
        ("Basic", {"fields": ("name", "slug", "category", "subcategory", "city")}),
        ("About", {"fields": ("description", "about_heading","about", "services", "features",
                              "established_year", "payment_methods")}),
        ("Contact", {"fields": ("address", "phone", "whatsapp", "email", "website")}),
        ("Media & map", {"fields": ("logo", "logo_bg_color", "logo_preview",
                                    "cover_image", "latitude", "longitude")}),
        ("Status", {"fields": ("owner", "rating", "review_count",
                               "is_verified", "is_featured", "is_active")}),
    )

    @admin.display(description="Logo preview (updates after saving)")
    def logo_preview(self, obj):
        if not obj or not obj.pk:
            return "Save the business first to see the preview."
        box = ("display:inline-grid;place-items:center;height:80px;width:80px;box-sizing:border-box;"
               "padding:4px;border:1px solid #ccc;border-radius:10px;overflow:hidden;")
        if obj.logo:
            return format_html(
                '<span style="{}background:{}"><img src="{}" '
                'style="display:block;width:100%;height:100%;object-fit:contain"></span>',
                box, obj.logo_background, obj.logo.url,
            )
        return format_html(
            '<span style="{}background:{};color:{};font-size:28px;font-weight:700">{}</span>',
            box, obj.logo_background, obj.logo_text_color, obj.initials,
        )

    @admin.action(description="Set default hours (9 AM - 9 PM, all 7 days)")
    def set_default_hours(self, request, queryset):
        for business in queryset:
            for day in range(7):
                OpeningHour.objects.get_or_create(
                    business=business, day=day,
                    defaults={"opens": time(9, 0), "closes": time(21, 0)},
                )

    @admin.action(description="Approve selected businesses (make them live)")
    def approve_selected(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} business(es) approved.")

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("business", "name", "rating", "is_approved", "created_at")
    list_filter = ("is_approved", "rating")

User = get_user_model()
admin.site.unregister(User)


class ProfileInline(admin.StackedInline):
    model = Profile
    fk_name = "user"
    can_delete = False
    fields = ("status", "reason", "status_changed_by", "status_changed_at")
    readonly_fields = ("status_changed_by", "status_changed_at")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    ordering = ("-date_joined",)
    list_select_related = ("profile",)
    list_display = (
        "email", "username", "account_status", "listings",
        "date_joined", "last_login", "is_active",
    )
    list_filter = ("profile__status", "is_active", "is_staff", "date_joined")
    search_fields = ("email", "username", "first_name", "last_name")
    actions = ["approve_users", "block_users", "unblock_users", "force_logout"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            n_listings=Count("businesses", distinct=True)
        )

    @admin.display(description="Status", ordering="profile__status")
    def account_status(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.get_status_display() if profile else "Approved"

    @admin.display(description="Listings", ordering="n_listings")
    def listings(self, obj):
        return obj.n_listings

    # ----- safety rules -----
    def get_inline_instances(self, request, obj=None):
        # the profile is created automatically, so hide it on the "add user" page
        return super().get_inline_instances(request, obj) if obj else []

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:  # moderators can't promote anyone
            fields += ["is_superuser", "is_staff", "groups", "user_permissions"]
        return fields

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # block instead of deleting

    def save_formset(self, request, form, formset, change):
        for obj in formset.save(commit=False):
            if isinstance(obj, Profile):
                obj.status_changed_by = request.user
            obj.save()
        formset.save_m2m()

    # ----- actions -----
    @admin.action(description="Approve selected users", permissions=["change"])
    def approve_users(self, request, queryset):
        n = 0
        for user in queryset:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.set_status(Profile.Status.APPROVED, by=request.user)
            n += 1
        self.message_user(request, f"{n} user(s) approved.")

    @admin.action(description="Block selected users (hides their listings)", permissions=["change"])
    def block_users(self, request, queryset):
        targets = queryset.exclude(is_superuser=True).exclude(pk=request.user.pk)
        skipped = queryset.count() - targets.count()
        n = 0
        for user in targets:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.set_status(Profile.Status.BLOCKED, by=request.user, reason="Blocked by admin")
            n += 1
        self.message_user(request, f"{n} user(s) blocked and their listings hidden.")
        if skipped:
            self.message_user(
                request, f"{skipped} superuser/own account(s) were skipped.", messages.WARNING
            )

    @admin.action(description="Unblock selected users", permissions=["change"])
    def unblock_users(self, request, queryset):
        n = 0
        for user in queryset:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.set_status(Profile.Status.APPROVED, by=request.user)
            n += 1
        self.message_user(
            request,
            f"{n} user(s) unblocked. Their listings stay hidden until you approve them in Businesses.",
        )

    @admin.action(description="Log selected users out everywhere", permissions=["change"])
    def force_logout(self, request, queryset):
        ids = {str(pk) for pk in queryset.exclude(pk=request.user.pk).values_list("pk", flat=True)}
        n = 0
        for session in Session.objects.filter(expire_date__gte=timezone.now()):
            if session.get_decoded().get("_auth_user_id") in ids:
                session.delete()
                n += 1
        self.message_user(request, f"{n} session(s) ended.")
        
@admin.register(BusinessPhoto)
class BusinessPhotoAdmin(admin.ModelAdmin):
    list_display = ("preview", "heading", "business", "category", "city")
    list_filter = ("business__category", "business__city")
    search_fields = ("business__name", "caption")
    raw_id_fields = ("business",)
    list_select_related = ("business__category", "business__city")

    @admin.display(description="Photo")
    def preview(self, obj):
        if not obj.image:
            return "-"
        return format_html('<img src="{}" style="height:50px;border-radius:4px">', obj.image.url)

    @admin.display(description="Category")
    def category(self, obj):
        return obj.business.category.name

    @admin.display(description="City")
    def city(self, obj):
        return obj.business.city.name