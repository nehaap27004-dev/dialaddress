from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from directory.models import RESERVED_SLUGS, City, Country


class Command(BaseCommand):
    help = "Shorten city slugs for /country/city/ URLs. Shows a plan; changes nothing without --apply."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **opts):
        for c in Country.objects.filter(slug__in=RESERVED_SLUGS):
            self.stdout.write(self.style.ERROR(f"Country '{c.name}' has slug '{c.slug}', which the site uses. Rename it."))

        cities = list(City.objects.select_related("country").order_by("pk"))

        def candidates(c):
            code = c.country.code if c.country else ""
            names = [c.name, f"{c.name} {c.state}", f"{c.name} {c.state} {code}"]
            return [s for s in (slugify(n) for n in names) if s]

        used = {}
        for c in cities:                       # slugs that are already clean stay as they are
            if c.slug in candidates(c) and c.slug not in used:
                used[c.slug] = c.pk

        plan = []
        for c in cities:
            if c.country_id is None:
                self.stdout.write(self.style.WARNING(f"No country: {c.name} (id {c.pk}). It can't get a clean URL."))
                continue
            if used.get(c.slug) == c.pk:
                continue
            for cand in candidates(c):
                if cand not in used:
                    used[cand] = c.pk
                    plan.append((c, cand))
                    break
            else:
                self.stdout.write(self.style.WARNING(f"No free slug for {c.name} (id {c.pk})."))

        for c, new in plan:
            self.stdout.write(f"{c.country.slug}: {c.slug}  ->  {new}")
        if not plan:
            self.stdout.write("Nothing to change.")
        elif opts["apply"]:
            with transaction.atomic():
                for c, _ in plan:
                    City.objects.filter(pk=c.pk).update(slug=f"tmp-{c.pk}")   # avoids unique clashes
                for c, new in plan:
                    City.objects.filter(pk=c.pk).update(slug=new)
            self.stdout.write(self.style.SUCCESS(f"Updated {len(plan)} cities."))
        else:
            self.stdout.write("Dry run. Run again with --apply to save these.")