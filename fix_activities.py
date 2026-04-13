from event.models import Activity
from django.db import transaction

def run():
    activities = Activity.objects.filter(organizer__isnull=True)
    count = 0
    with transaction.atomic():
        for a in activities:
            a.organizer = a.event.user
            a.save()
            count += 1
    print(f'Assigned {count} activities to their event owners.')

if __name__ == "__main__":
    run()
