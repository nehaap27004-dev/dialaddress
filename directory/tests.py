import base64
import re
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import BusinessForm
from .models import Business, Category, City

# a real 1x1 PNG
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
TMP_MEDIA = tempfile.mkdtemp()


def make_business(**extra):
    category, _ = Category.objects.get_or_create(name="Automobile")
    city, _ = City.objects.get_or_create(name="Gurgaon", state="Haryana")
    data = dict(name="Tata Motors", category=category, city=city,
                address="Sector 29", phone="9876543210")
    data.update(extra)
    return Business.objects.create(**data)


def png(name="logo.png"):
    return SimpleUploadedFile(name, PNG, content_type="image/png")


def tag(html, css_class):
    """The opening HTML tag that carries the given class attribute."""
    m = re.search(r'<[a-z]+[^>]*class="%s"[^>]*>' % re.escape(css_class), html)
    return m.group(0) if m else ""


@override_settings(MEDIA_ROOT=TMP_MEDIA, REQUIRE_USER_APPROVAL=False)
class LogoColorTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    # ---------- data / defaults ----------
    def test_default_is_pure_white(self):
        b = make_business()
        b.refresh_from_db()
        self.assertEqual(b.logo_bg_color, "#FFFFFF")
        self.assertEqual(b.logo_background, "#FFFFFF")

    def test_bad_values_fall_back_to_white(self):
        b = make_business()
        for bad in ["", "red", "#12", "#GGGGGG", "ffffff", "#FFFFFFF", None]:
            b.logo_bg_color = bad
            self.assertEqual(b.logo_background, "#FFFFFF", f"display for {bad!r}")
            b.save()
            b.refresh_from_db()
            self.assertEqual(b.logo_bg_color, "#FFFFFF", f"stored value for {bad!r}")

    def test_valid_color_is_stored_in_upper_case(self):
        b = make_business(logo_bg_color="#1f5fd1")
        b.refresh_from_db()
        self.assertEqual(b.logo_bg_color, "#1F5FD1")

    def test_text_color_is_readable(self):
        self.assertEqual(make_business(logo_bg_color="#FFFFFF").logo_text_color, "#1b2430")
        self.assertEqual(make_business(name="B", logo_bg_color="#000000").logo_text_color, "#FFFFFF")
        self.assertEqual(make_business(name="C", logo_bg_color="#0B2A5C").logo_text_color, "#FFFFFF")

    # ---------- forms ----------
    def _form(self, color, instance=None):
        b = instance or make_business()
        data = {"name": b.name, "category": b.category_id, "city": b.city_id,
                "address": b.address, "phone": b.phone, "logo_bg_color": color}
        return BusinessForm(data, instance=b)

    def test_form_has_the_color_field_as_a_color_input(self):
        form = BusinessForm()
        self.assertIn("logo_bg_color", form.fields, "logo_bg_color is missing from BusinessForm.Meta.fields")
        self.assertIn('type="color"', str(form["logo_bg_color"]))

    def test_form_saves_a_valid_color(self):
        form = self._form("#ff0000")
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        form.instance.refresh_from_db()
        self.assertEqual(form.instance.logo_bg_color, "#FF0000")

    def test_form_rejects_a_bad_color(self):
        form = self._form("red")
        self.assertFalse(form.is_valid())
        self.assertIn("logo_bg_color", form.errors)

    def test_blank_color_is_saved_as_white(self):
        form = self._form("")
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        form.instance.refresh_from_db()
        self.assertEqual(form.instance.logo_bg_color, "#FFFFFF")

    # ---------- display ----------
    def test_card_shows_color_around_an_uploaded_logo(self):
        b = make_business(logo_bg_color="#FF0000", logo=png())
        html = render_to_string("directory/_card.html", {"b": b})
        self.assertIn("background:#FF0000", tag(html, "logo-box"))
        self.assertIn("<img", html)  # the logo itself is still shown

    def test_card_without_logo_shows_initials_on_the_color(self):
        b = make_business(logo_bg_color="#000000")
        html = render_to_string("directory/_card.html", {"b": b})
        t = tag(html, "logo-box")
        self.assertIn("background:#000000", t)
        self.assertIn("color:#FFFFFF", t)
        self.assertIn("TM", html)

    def test_card_default_is_white(self):
        html = render_to_string("directory/_card.html", {"b": make_business()})
        self.assertIn("background:#FFFFFF", tag(html, "logo-box"))

    def test_detail_page_shows_the_color_with_and_without_logo(self):
        with_logo = make_business(name="With Logo", logo_bg_color="#00AA55", logo=png("a.png"))
        no_logo = make_business(name="No Logo", logo_bg_color="#FFD400")
        for b, expected in ((with_logo, "#00AA55"), (no_logo, "#FFD400")):
            html = self.client.get(reverse("business_detail", args=[b.slug])).content.decode()
            self.assertIn(f"background:{expected}", tag(html, "logo-box logo-lg"), b.name)

    # ---------- whole data flow: owner edit page -> database ----------
    def test_owner_edit_saves_the_color_and_keeps_the_logo(self):
        user = get_user_model().objects.create_user("owner", "o@example.com", "pass12345")
        b = make_business(owner=user, logo=png())
        old_logo = b.logo.name
        self.client.force_login(user)
        url = reverse("edit_business", args=[b.slug])
        base = {"name": b.name, "category": b.category_id, "city": b.city_id,
                "address": b.address, "phone": b.phone}

        r = self.client.post(url, {**base, "logo_bg_color": "#00ff00"})
        self.assertEqual(r.status_code, 302, "the edit form did not validate, so nothing was saved")
        b.refresh_from_db()
        self.assertEqual(b.logo_bg_color, "#00FF00")
        self.assertEqual(b.logo.name, old_logo, "changing only the color must not remove the logo")

        r = self.client.post(url, {**base, "logo_bg_color": "#ffffff"})  # reset to white
        self.assertEqual(r.status_code, 302)
        b.refresh_from_db()
        self.assertEqual(b.logo_bg_color, "#FFFFFF")

    # ---------- admin ----------
    def test_admin_page_has_a_color_picker_and_loads_its_script(self):
        admin_user = get_user_model().objects.create_superuser("boss", "b@example.com", "pass12345")
        self.client.force_login(admin_user)
        b = make_business()
        html = self.client.get(reverse("admin:directory_business_change", args=[b.pk])).content.decode()
        m = re.search(r'<input[^>]*name="logo_bg_color"[^>]*>', html)
        self.assertIsNotNone(m, "no logo_bg_color input on the admin page")
        self.assertIn('type="color"', m.group(0))
        self.assertIn("logo_color.js", html,
                      "the picker script is not loaded: 'class Media' must be INSIDE BusinessAdmin")