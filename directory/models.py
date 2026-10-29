from decimal import Decimal
from urllib.parse import quote
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db import models
from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings
import os
import uuid
import re
from django.core.validators import RegexValidator
# Top-level words the site uses itself. A country can't use one of these as its slug.
RESERVED_SLUGS = {
    "admin", "dashboard", "business", "search", "login", "logout", "signup",
    "add-business", "my-businesses", "photos", "category", "city",
    "static", "media", "sitemap", "robots", "api",
}
DEFAULT_LOGO_BG = "#FFFFFF"
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def normalize_color(value):
    """A valid #RRGGBB in upper case, or pure white for anything else."""
    value = (value or "").strip()
    return value.upper() if _HEX.match(value) else DEFAULT_LOGO_BG
class CategoryGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers show first.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.CharField(
        max_length=50, blank=True,
        help_text="Icon class name, e.g. 'fa-utensils'"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True,
        related_name="children",
        help_text="Leave empty for a main category. Set it to make a subcategory (e.g. Fast Food under Restaurants).",
    )
    order = models.PositiveIntegerField(
        "Order", default=0,
        help_text="Lower numbers show first (1, 2, 3...). Categories with the same number are sorted by name.",
    )
    group = models.ForeignKey(
        "CategoryGroup", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="categories",
        help_text="Optional. Groups main categories, e.g. Food & Dining.",
    )
    info_heading = models.CharField(
        "Panel heading", max_length=150, blank=True, default="",
        help_text="Heading shown in the More panel. Leave empty to use About plus the category name.",
    )
    info_subheading = models.CharField(
        "Panel subheading", max_length=250, blank=True, default="",
        help_text="One line shown under the heading.",
    )
    info_content = models.TextField(
        "Panel description", blank=True, default="",
        help_text="Separate paragraphs with a blank line. The More button only appears when this is filled in.",
    )
    class Meta:
        verbose_name_plural = "categories"
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

   
    @property
    def has_info(self):
        return bool(self.info_content.strip())

    @property
    def info_title(self):
        return self.info_heading or f"About {self.name}"

    def clean(self):
        p = self.parent
        while p is not None:
            if p.pk == self.pk:
                raise ValidationError({"parent": "A category can't be placed under itself or one of its own subcategories."})
            p = p.parent
    def __str__(self):
        return f"{self.parent.name} › {self.name}" if self.parent else self.name

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(
        max_length=2, unique=True,
        help_text="2-letter ISO code, e.g. IN, US, AE"
    )
    slug = models.SlugField(max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "countries"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        self.code = self.code.upper()
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError
        s = self.slug or slugify(self.name)
        if s in RESERVED_SLUGS:
            raise ValidationError({"name": f'"{s}" is used by the site itself. Choose a different name.'})

    def get_absolute_url(self):
        return reverse("geo_country", args=[self.slug])
    def __str__(self):
        return self.name

class City(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE,
        related_name="cities", null=True
    )
    name = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(max_length=150, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "cities"
        ordering = ["name"]
        unique_together = ("country", "name", "state")

    def save(self, *args, **kwargs):
        if not self.slug:
            code = self.country.code if self.country else ""
            candidates = [self.name, f"{self.name} {self.state}", f"{self.name} {self.state} {code}"]
            for c in candidates:
                s = slugify(c)
                if s and not City.objects.filter(slug=s).exclude(pk=self.pk).exists():
                    self.slug = s          # shortest free slug: muscat, then muscat-xyz, then muscat-xyz-om
                    break
            else:
                self.slug = slugify(f"{self.name}-{self.state}-{code}-{uuid.uuid4().hex[:4]}")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.country_id:
            return reverse("geo_city", args=[self.country.slug, self.slug])
        return reverse("city_page", args=[self.slug])

    def __str__(self):
        parts = [self.name, self.state, self.country.name if self.country else ""]
        return ", ".join(p for p in parts if p)
class Feature(models.Model):
    name = models.CharField(max_length=60, unique=True)
    icon = models.CharField(
        max_length=50, default="fa-check",
        help_text="Font Awesome class, e.g. fa-utensils, fa-bag-shopping, fa-truck",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
    
class Business(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="businesses",
        limit_choices_to={"parent__isnull": True},
    )
    subcategory = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sub_businesses",
        limit_choices_to={"parent__isnull": False},
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="businesses",
        help_text="User who submitted this listing (empty for listings you add yourself).",
    )
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, related_name="businesses"
    )
    description = models.TextField(blank=True)
    about_heading = models.CharField(
        "About heading", max_length=150, blank=True, default="",
        help_text="Optional heading shown under 'About Us', e.g. 'Serving Delhi since 1990'.",
    )
    about = models.TextField(
        blank=True, help_text="Long 'About Us' text. If empty, the short description is used."
    )
    features = models.ManyToManyField(Feature, blank=True, related_name="businesses")
    services = models.TextField(
        blank=True, help_text="Comma separated, e.g. Burgers, Beverages, Fast Food"
    )
    established_year = models.PositiveSmallIntegerField(null=True, blank=True)
    payment_methods = models.CharField(
        max_length=300, blank=True,
        help_text="Comma separated, e.g. Cash, UPI, Credit/Debit Cards",
    )
    address = models.CharField(max_length=300)
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(
        max_length=20, blank=True,
        help_text="Number with country code, e.g. 919876543210"
    )
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)
    logo_bg_color = models.CharField(
        "Logo background color", max_length=7, default="#FFFFFF", blank=True,
        validators=[RegexValidator(r"^#[0-9a-fA-F]{6}$", "Enter a color like #FFFFFF.")],
        help_text="Background shown behind the logo (or the initials when there is no logo). Default is pure white.",
    )
    cover_image = models.ImageField(upload_to="covers/", blank=True, null=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, blank=True, null=True
    )
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    review_count = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True, editable=False)
    class Meta:
        verbose_name_plural = "businesses"
        ordering = ["-is_featured", "-rating", "name"]
        indexes = [models.Index(fields=["is_active", "-created_at"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.name}-{self.city.name}")
            slug = base
            n = 1
            while Business.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        self.updated_at = timezone.now()
        self.logo_bg_color = normalize_color(self.logo_bg_color)
        super().save(*args, **kwargs)
    @property
    def service_list(self):
        return [s.strip() for s in self.services.split(",") if s.strip()]

    @property
    def payment_list(self):
        return [s.strip() for s in self.payment_methods.split(",") if s.strip()]

    @property
    def full_address(self):
        return f"{self.address}, {self.city}"

    @property
    def map_embed_url(self):
        if self.latitude is not None and self.longitude is not None:
            q = f"{self.latitude},{self.longitude}"
        else:
            q = quote(f"{self.name} {self.address} {self.city.name}")
        return f"https://www.google.com/maps?q={q}&output=embed"

    @property
    def open_now(self):
        """True = open, False = closed, None = no hours entered for today."""
        now = timezone.localtime()
        for h in self.hours.all():
            if h.day != now.weekday():
                continue
            if h.is_closed or not (h.opens and h.closes):
                return False
            t = now.time()
            if h.opens < h.closes:
                return h.opens <= t <= h.closes
            return t >= h.opens or t <= h.closes  # closes at/after midnight
        return None
    @property
    def maps_url(self):
        if self.latitude is not None and self.longitude is not None:
            return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
        return "https://www.google.com/maps/search/?api=1&query=" + quote(
            f"{self.name} {self.address}"
        )

    @property
    def whatsapp_url(self):
        number = "".join(ch for ch in self.whatsapp if ch.isdigit())
        return f"https://wa.me/{number}" if number else ""

    @property
    def review_display(self):
        n = self.review_count
        if n >= 1000:
            return f"{n / 1000:.1f}K".replace(".0K", "K")
        return str(n)
    #Visitor reviews with automatic ratings
    def refresh_rating(self):
        stats = self.reviews.filter(is_approved=True).aggregate(
            avg=Avg("rating"), n=Count("id")
        )
        avg = Decimal(str(round(stats["avg"] or 0, 1)))
        Business.objects.filter(pk=self.pk).update(
            rating=avg, review_count=stats["n"]
        )
    @property
    def initials(self):
        words = [w for w in self.name.split() if w[0].isalnum()]
        if not words:
            return "?"
        if len(words) == 1:
            return words[0][:2].upper()
        return (words[0][0] + words[1][0]).upper()

    @property
    def logo_background(self):
        return normalize_color(self.logo_bg_color)

    @property
    def logo_text_color(self):
        h = self.logo_background.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return "#1b2430" if (r * 299 + g * 587 + b * 114) / 1000 > 150 else "#FFFFFF"
    
    def __str__(self):
        return self.name


    
    
def photo_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"photos/{instance.business.slug}-{uuid.uuid4().hex[:8]}{ext}"


class BusinessPhoto(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=photo_path)
    heading = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Bold title shown under the photo, e.g. 'Family dining area'",
    )
    caption = models.CharField(
        "Short details", max_length=300, blank=True, default="",
        help_text="One or two sentences shown under the heading",
    )

    class Meta:
        ordering = ["id"]

    @property
    def display_caption(self):
        """Used as the image alt text."""
        b = self.business
        return self.heading or self.caption or f"{b.name} – {b.category.name} in {b.city.name}"

    def __str__(self):
        return f"{self.business.name} photo"
    def _fmt(t):
       return t.strftime("%I:%M %p").lstrip("0")

class OpeningHour(models.Model):
    DAYS = [
        (0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
        (4, "Friday"), (5, "Saturday"), (6, "Sunday"),
    ]
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="hours")
    day = models.PositiveSmallIntegerField(choices=DAYS)
    opens = models.TimeField(null=True, blank=True)
    closes = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["day"]
        unique_together = ("business", "day")

    @property
    def label(self):
        if self.is_closed or not (self.opens and self.closes):
            return "Closed"

        def fmt(t):
            return t.strftime("%I:%M %p").lstrip("0")

        return f"{fmt(self.opens)} – {fmt(self.closes)}"

class Review(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="reviews")
    name = models.CharField(max_length=100)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.business.name} ({self.rating}★)"
#This runs whenever a review is added, edited, approved, unapproved, or deleted, including from the admin
@receiver([post_save, post_delete], sender=Review)
def update_business_rating(sender, instance, **kwargs):
    instance.business.refresh_rating()

class Profile(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending approval"
        APPROVED = "approved", "Approved"
        BLOCKED = "blocked", "Blocked"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.APPROVED, db_index=True
    )
    reason = models.CharField("Note / reason", max_length=255, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if self.user.is_superuser:  # a superuser can never be blocked or held back
            self.status = self.Status.APPROVED
        if self.pk:
            old = Profile.objects.filter(pk=self.pk).values_list("status", flat=True).first()
            if old != self.status:
                self.status_changed_at = timezone.now()
        super().save(*args, **kwargs)

        # Blocking = the account stops working and their listings are hidden
        user = self.user
        active = self.status != self.Status.BLOCKED
        if user.is_active != active:
            user.is_active = active
            user.save(update_fields=["is_active"])
        if self.status == self.Status.BLOCKED:
            user.businesses.filter(is_active=True).update(is_active=False)

    def set_status(self, status, by=None, reason=""):
        self.status = status
        self.status_changed_by = by
        self.reason = reason
        self.save()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        needs_approval = getattr(settings, "REQUIRE_USER_APPROVAL", False) and not instance.is_staff
        Profile.objects.create(
            user=instance,
            status=Profile.Status.PENDING if needs_approval else Profile.Status.APPROVED,
        )