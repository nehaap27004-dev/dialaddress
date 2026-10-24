import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Business, Category, Feature, Review

User = get_user_model()


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_username(self):
        username = self.cleaned_data["username"]
        if "@" in username:
            raise forms.ValidationError(
                "Username can't contain @. You can log in with your email instead."
            )
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or username",
        widget=forms.TextInput(
            attrs={"autofocus": True, "placeholder": "Email or username"}
        ),
    )

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError(
                "This account has been blocked. Please contact support.",
                code="inactive",
            )
class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=[(i, str(i)) for i in range(5, 0, -1)],
        coerce=int,
        widget=forms.RadioSelect,
        error_messages={"required": "Please choose a star rating."},
    )

    class Meta:
        model = Review
        fields = ["name", "rating", "comment"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Your name", "maxlength": 100}),
            "comment": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Share your experience (optional)"}
            ),
        }


class BusinessForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(parent__isnull=True)
    )
    subcategory = forms.ModelChoiceField(
        queryset=Category.objects.filter(parent__isnull=False), required=False
    )
    features = forms.ModelMultipleChoiceField(
        queryset=Feature.objects.all(), required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Business
        fields = [
            "name", "category", "subcategory", "city",
            "description","about_heading", "about", "services", "features",
            "established_year", "payment_methods",
            "address", "phone", "whatsapp", "email", "website",
            "logo", "logo_bg_color", "cover_image", "latitude", "longitude",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "about_heading": forms.TextInput(attrs={"placeholder": "About heading"}),
            "about": forms.Textarea(attrs={"rows": 4}),
            "services": forms.Textarea(attrs={"rows": 2}),
            "logo_bg_color": forms.TextInput(attrs={
                "type": "color",
                "style": "width:70px;height:40px;padding:2px;cursor:pointer;",
            }),
        }

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not 8 <= len(re.sub(r"\D", "", phone)) <= 15:
            raise forms.ValidationError("Enter a valid phone number.")
        return phone

    def clean_whatsapp(self):
        # store digits only, e.g. 919876543210
        return re.sub(r"\D", "", self.cleaned_data.get("whatsapp", ""))

    def _check_image(self, name):
        f = self.cleaned_data.get(name)
        if f and hasattr(f, "size") and f.size > 3 * 1024 * 1024:
            raise forms.ValidationError("Image must be smaller than 3 MB.")
        return f

    def clean_logo(self):
        return self._check_image("logo")

    def clean_cover_image(self):
        return self._check_image("cover_image")

    def clean(self):
        data = super().clean()
        cat, sub = data.get("category"), data.get("subcategory")
        if cat and sub and sub.parent_id != cat.id:
            self.add_error("subcategory", "This subcategory doesn't belong to the chosen category.")
        return data