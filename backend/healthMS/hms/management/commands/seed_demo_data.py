from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from django.conf import settings

from hms.models import Patient
from lis.models import LabTestCatalog

CATALOG = [
    ("CBC", "Complete Blood Count"),
    ("LFT", "Liver Function Test"),
    ("RFT", "Renal Function Test"),
    ("BS", "Blood Sugar (Fasting)"),
    ("LIP", "Lipid Profile"),
    ("URM", "Urinalysis (Microscopy)"),
]


class Command(BaseCommand):
    help = "Seed lab test catalog, service accounts and demo patients."

    def handle(self, *args, **options):
        # 1. Lab test catalog
        for code, name in CATALOG:
            obj, created = LabTestCatalog.objects.get_or_create(
                code=code, defaults={"name": name}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  + catalog: {code} - {name}"))

        # 2. Service accounts
        lab_admin, created = User.objects.get_or_create(
            username="lab_admin",
            defaults={"is_staff": True, "is_superuser": True},
        )
        if created:
            lab_admin.set_password(settings.DEMO_LAB_ADMIN_PASSWORD)
            lab_admin.save()
            self.stdout.write(self.style.SUCCESS("  + user: lab_admin"))

        hms_user, created = User.objects.get_or_create(
            username=settings.LIS_SERVICE_USERNAME
        )
        if created:
            hms_user.set_password(settings.LIS_SERVICE_PASSWORD)
            hms_user.save()
            self.stdout.write(self.style.SUCCESS(
                f"  + user: {settings.LIS_SERVICE_USERNAME} (HMS service account)"
            ))

        # 3. Demo patients
        patients = [
            ("HMS-0001", "Amina", "Juma", "1990-04-12", "F"),
            ("HMS-0002", "Baraka", "Mushi", "1985-11-30", "M"),
            ("HMS-0003", "Neema", "Kileo", "2001-07-08", "F"),
        ]
        for pn, fn, ln, dob, gender in patients:
            _, created = Patient.objects.get_or_create(
                patient_number=pn,
                defaults={
                    "first_name": fn,
                    "last_name": ln,
                    "date_of_birth": dob,
                    "gender": gender,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  + patient: {pn} {fn} {ln}"))

        self.stdout.write(self.style.SUCCESS("Seed complete."))
