from django import forms
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from directory.forms import BusinessForm
from directory.models import Category, CategoryGroup
from directory.models import Category, CategoryGroup, City, Country, Feature, Review
User = get_user_model()


class StyledFormMixin:
    """Adds the dashboard input style to every text-like widget."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        skip = (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect, forms.FileInput)
        for field in self.fields.values():
            if not isinstance(field.widget, skip):
                css = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = f"{css} dash-input".strip()


class BusinessManageForm(StyledFormMixin, BusinessForm):
    class Meta(BusinessForm.Meta):
        fields = BusinessForm.Meta.fields + ["owner", "is_verified", "is_featured", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = User.objects.order_by("username")


class CategoryGroupForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CategoryGroup
        fields = ["name", "slug", "order", "is_active"]

    def clean_slug(self):
        return self.cleaned_data.get("slug") or slugify(self.cleaned_data.get("name", ""))


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug", "icon", "parent", "group", "order",
                  "info_heading", "info_subheading", "info_content"]
        widgets = {"info_content": forms.Textarea(attrs={"rows": 6})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parents = Category.objects.filter(parent__isnull=True)  # the site has two levels only
        if self.instance.pk:
            parents = parents.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = parents

    def clean_slug(self):
        return self.cleaned_data.get("slug") or slugify(self.cleaned_data.get("name", ""))

    def clean(self):
        data = super().clean()
        if data.get("parent") and self.instance.pk and self.instance.children.exists():
            self.add_error("parent", "This category has subcategories, so it can't become a subcategory itself.")
        return data


class UserManageForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_staff", "groups"]
        widgets = {"groups": forms.CheckboxSelectMultiple}

    def __init__(self, *args, acting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not (acting_user and acting_user.is_superuser):  # only superusers set roles
            self.fields.pop("is_staff")
            self.fields.pop("groups")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account already uses this email.")
        return email
class CountryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Country
        fields = ["name", "code"]


class CityForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = City
        fields = ["country", "name", "state"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["country"].required = True


class FeatureForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Feature
        fields = ["name", "icon"]


class ReviewManageForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Review
        fields = ["name", "rating", "comment", "is_approved"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 4})}