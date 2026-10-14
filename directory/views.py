from datetime import datetime
from decimal import Decimal

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from .decorators import approved_required
from .forms import BusinessForm, ReviewForm, SignUpForm
from .models import Business, BusinessPhoto, Category, City, OpeningHour
PER_PAGE = 9

SORTS = {
    "relevance": ("-is_featured", "-rating", "name"),
    "rating": ("-rating", "-review_count", "name"),
    "reviews": ("-review_count", "-rating", "name"),
    "newest": ("-created_at",),
    "name": ("name",),
}


def _cities():
    return City.objects.select_related("country").order_by("country__name", "name")


def home(request):
    context = {
        "categories": Category.objects.filter(parent__isnull=True)[:8],
        "cities": _cities(),
        "featured": Business.objects.filter(is_active=True, is_featured=True)
        .select_related("category", "city")[:6],
    }
    return render(request, "directory/home.html", context)
#Search filters, sorting, and pagination
#This step adds a filter sidebar (category, minimum rating, verified only), sorting, and page numbers to the search page. The search box also matches more fields. No migrations are needed.
def search(request):
    q = request.GET.get("q", "").strip()
    city_id = request.GET.get("city", "")
    category_slug = request.GET.get("category", "")
    min_rating = request.GET.get("rating", "")
    verified = request.GET.get("verified") == "1"
    sort = request.GET.get("sort", "relevance")
    if sort not in SORTS:
        sort = "relevance"

    results = Business.objects.filter(is_active=True).select_related("category", "city")

    if q:
        results = results.filter(
            Q(name__icontains=q)
            | Q(description__icontains=q)
            | Q(services__icontains=q)
            | Q(address__icontains=q)
            | Q(category__name__icontains=q)
            | Q(subcategory__name__icontains=q)
            | Q(city__name__icontains=q)
        )
    if city_id.isdigit():
        results = results.filter(city_id=city_id)
    if category_slug:
        results = results.filter(
            Q(category__slug=category_slug) | Q(subcategory__slug=category_slug)
        )
    if min_rating in ("3", "4", "4.5"):
        results = results.filter(rating__gte=Decimal(min_rating))
    if verified:
        results = results.filter(is_verified=True)

    results = results.order_by(*SORTS[sort])

    paginator = Paginator(results, PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "page_obj": page_obj,
        "total": paginator.count,
        "page_range": list(
            paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1)
        ),
        "ellipsis": Paginator.ELLIPSIS,
        "querystring": params.urlencode(),
        "q": q,
        "selected_city": city_id,
        "category_slug": category_slug,
        "min_rating": min_rating,
        "verified": verified,
        "sort": sort,
        "cities": _cities(),
        "category_tree": Category.objects.filter(parent__isnull=True).prefetch_related("children"),
    }
    return render(request, "directory/search.html", context)

def business_detail(request, slug):
    business = get_object_or_404(
        Business.objects.select_related("category", "subcategory", "city__country")
        .prefetch_related("features", "photos", "hours", "reviews"),
        slug=slug,
    )
    if not business.is_active:
        u = request.user
        if not (u.is_authenticated and (business.owner_id == u.id or u.is_staff)):
            raise Http404

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if request.POST.get("company"):  # hidden spam trap, real users leave it empty
            return redirect(reverse("business_detail", args=[business.slug]))
        if form.is_valid():
            review = form.save(commit=False)
            review.business = business
            review.save()
            messages.success(request, "Thank you! Your review has been posted.")
            return redirect(reverse("business_detail", args=[business.slug]) + "#reviews")
    else:
        form = ReviewForm()

    photos = list(business.photos.all())
    reviews = [r for r in business.reviews.all() if r.is_approved]
    related = (
        Business.objects.filter(is_active=True, category=business.category)
        .exclude(pk=business.pk)
        .select_related("category", "city")[:3]
    )
    return render(request, "directory/business_detail.html", {
        "b": business,
        "form": form,
        "photos": photos,
        "thumbs": photos[:4],
        "extra_photos": max(len(photos) - 4, 0),
        "hours": business.hours.all(),
        "today": timezone.localtime().weekday(),
        "open_now": business.open_now,
        "reviews": reviews[:10],
        "related": related,
    })
FORM_SECTIONS = [
    ("Basic details", ["name", "category", "subcategory", "city"]),
    ("About your business", ["description", "about", "services", "features",
                             "established_year", "payment_methods"]),
    ("Contact", ["address", "phone", "whatsapp", "email", "website"]),
    ("Images & map (optional)", ["logo", "cover_image", "latitude", "longitude"]),
]
WIDE_FIELDS = {"description", "about", "services", "features", "address", "payment_methods"}


def _form_context(form, title, submit_label):
    sections = [
        (heading, [(form[n], n in WIDE_FIELDS) for n in names])
        for heading, names in FORM_SECTIONS
    ]
    return {"form": form, "sections": sections,
            "page_title": title, "submit_label": submit_label}


def signup(request):
    if request.user.is_authenticated:
        return redirect("my_businesses")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        if user.profile.status == "pending":
            messages.success(
                request,
                "Account created! An admin needs to approve it before you can add a business.",
            )
            return redirect("my_businesses")
        messages.success(request, "Welcome! Your account has been created.")
        return redirect("add_business")
    return render(request, "directory/signup.html", {"form": form})
@login_required
@approved_required
def add_business(request):
    form = BusinessForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        business = form.save(commit=False)
        business.owner = request.user
        business.is_active = False  # hidden until an admin approves it
        business.save()
        form.save_m2m()
        messages.success(
            request, "Submitted! Your business will go live once it has been approved."
        )
        return redirect("my_businesses")
    return render(request, "directory/business_form.html",
                  _form_context(form, "Add your business", "Submit for approval"))


@login_required
@approved_required
def edit_business(request, slug):
    business = get_object_or_404(Business, slug=slug, owner=request.user)
    form = BusinessForm(request.POST or None, request.FILES or None, instance=business)
    if request.method == "POST" and form.is_valid():
        business = form.save(commit=False)
        business.is_active = False  # edits go back for approval
        business.save()
        form.save_m2m()
        messages.success(request, "Changes saved. The listing will be re-checked before going live.")
        return redirect("my_businesses")
    return render(request, "directory/business_form.html",
                  _form_context(form, f"Edit {business.name}", "Save changes"))


@login_required
def my_businesses(request):
    items = request.user.businesses.select_related("category", "city")
    return render(request, "directory/my_businesses.html", {"items": items})


MAX_PHOTOS = 12
MAX_IMAGE_MB = 3


def _managed_business(request, slug):
    """The owner (or an admin) may manage a business; everyone else gets a 404."""
    business = get_object_or_404(Business, slug=slug)
    if business.owner_id != request.user.id and not request.user.is_staff:
        raise Http404
    return business


def _parse_time(value):
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise ValueError(value)

#Opening hours and photos from the site
@login_required
@approved_required
def manage_hours(request, slug):
    business = _managed_business(request, slug)
    existing = {h.day: h for h in business.hours.all()}
    rows, errors, parsed = [], [], {}

    for day, label in OpeningHour.DAYS:
        if request.method == "POST":
            o_raw = request.POST.get(f"opens_{day}", "")
            c_raw = request.POST.get(f"closes_{day}", "")
            closed = request.POST.get(f"closed_{day}") == "on"
            try:
                opens, closes = _parse_time(o_raw), _parse_time(c_raw)
            except ValueError:
                errors.append(f"{label}: enter valid times.")
                opens = closes = None
            else:
                if not closed and (opens is None) != (closes is None):
                    errors.append(
                        f"{label}: enter both opening and closing time, or leave both empty."
                    )
            parsed[day] = (opens, closes, closed)
            rows.append({"day": day, "label": label,
                         "opens": o_raw, "closes": c_raw, "closed": closed})
        else:
            h = existing.get(day)
            rows.append({
                "day": day, "label": label,
                "opens": h.opens.strftime("%H:%M") if h and h.opens else "",
                "closes": h.closes.strftime("%H:%M") if h and h.closes else "",
                "closed": bool(h and h.is_closed),
            })

    if request.method == "POST" and not errors:
        for day, (opens, closes, closed) in parsed.items():
            if closed or (opens and closes):
                OpeningHour.objects.update_or_create(
                    business=business, day=day,
                    defaults={"opens": opens, "closes": closes, "is_closed": closed},
                )
            else:  # both empty and not closed: hide this day
                OpeningHour.objects.filter(business=business, day=day).delete()
        messages.success(request, "Opening hours saved.")
        return redirect("my_businesses")

    return render(request, "directory/manage_hours.html",
                  {"business": business, "rows": rows, "errors": errors})


@login_required
@approved_required
def manage_photos(request, slug):
    business = _managed_business(request, slug)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete" and request.POST.get("photo_id", "").isdigit():
            photo = get_object_or_404(
                BusinessPhoto, pk=int(request.POST["photo_id"]), business=business
            )
            photo.image.delete(save=False)  # remove the file from disk too
            photo.delete()
            messages.success(request, "Photo removed.")

        elif action == "upload":
            files = request.FILES.getlist("images")
            room = MAX_PHOTOS - business.photos.count()
            if not files:
                messages.error(request, "Choose at least one image.")
            elif len(files) > room:
                messages.error(
                    request,
                    f"You can add {max(room, 0)} more photo(s). The limit is {MAX_PHOTOS}.",
                )
            else:
                checker = forms.ImageField()
                added, problems = 0, []
                for f in files:
                    if f.size > MAX_IMAGE_MB * 1024 * 1024:
                        problems.append(f"{f.name} is larger than {MAX_IMAGE_MB} MB")
                        continue
                    try:
                        checker.clean(f)  # confirms it is a real image
                    except ValidationError:
                        problems.append(f"{f.name} is not a valid image")
                        continue
                    BusinessPhoto.objects.create(business=business, image=f)
                    added += 1
                if added:
                    messages.success(request, f"{added} photo(s) uploaded.")
                if problems:
                    messages.error(request, "Skipped: " + "; ".join(problems) + ".")

        return redirect("manage_photos", slug=business.slug)

    return render(request, "directory/manage_photos.html", {
        "business": business,
        "photos": business.photos.all(),
        "max_photos": MAX_PHOTOS,
        "max_mb": MAX_IMAGE_MB,
    })