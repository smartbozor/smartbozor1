from django.db import transaction

from apps.stall.models import Stall, StallStatus
from smartbozor.celery import app


def run_stall_reset_payment_progress(stall_id, stall_status_id):
    stall_reset_payment_progress.apply_async(
        args=[stall_id, stall_status_id],
        countdown=900
    )


@app.task()
def stall_reset_payment_progress(stall_id, stall_status_id):
    with transaction.atomic():
        stall = Stall.objects.select_for_update().get(pk=stall_id)
        ss = StallStatus.objects.get(pk=stall_status_id)
        if not ss.is_paid:
            ss.payment_progress = 0
            ss.save()

