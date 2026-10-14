from decimal import Decimal
from urllib.parse import quote

from django.db import models
from django.db.models import Avg, Count
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings

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

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

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
            parts = [self.name, self.state, self.country.code if self.country else ""]
            self.slug = slugify("-".join(p for p in parts if p))
        super().save(*args, **kwargs)

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

    class Meta:
        verbose_name_plural = "businesses"
        ordering = ["-is_featured", "-rating", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.name}-{self.city.name}")
            slug = base
            n = 1
            while Business.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
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
    def __str__(self):
        return self.name

class BusinessPhoto(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="photos/")
    caption = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ["id"]

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
        return f"{_fmt(self.opens)} – {_fmt(self.closes)}"

    def __str__(self):
        return f"{self.business.name} - {self.get_day_display()}"


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