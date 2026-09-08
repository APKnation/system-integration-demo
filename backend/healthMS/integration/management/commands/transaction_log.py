from django.core.management.base import BaseCommand

from integration.models import IntegrationLog


class Command(BaseCommand):
    help = "Print the integration transaction log."

    def add_arguments(self, parser):
        parser.add_argument("-n", "--limit", type=int, default=25)

    def handle(self, *args, **options):
        qs = IntegrationLog.objects.all()[: options["limit"]]
        if not qs:
            self.stdout.write("No transaction log entries yet.")
            return
        for entry in qs:
            line = (
                f"{entry.created_at:%Y-%m-%d %H:%M:%S}  {entry.method:<4}  "
                f"{entry.status_code}  {entry.status:<20}  {entry.endpoint}  "
                f"req={entry.request_id or '-'}"
            )
            self.stdout.write(line)
            if entry.error_message:
                self.stdout.write(f"    error: {entry.error_message}")
