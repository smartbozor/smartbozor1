from django.db import models


class Report(models.Model):
    class Meta:
        permissions = [
            ('can_view_total_revenue', "Can view total revenue"),
            ('can_view_total_scan', "Can view total scan"),
        ]
