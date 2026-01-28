from django.urls import path

from apps.report.views import ReportTotalRevenueView, ReportTotalScanView, ReportTotalClick

app_name = 'report'
urlpatterns = [
    path("total-revenue/", ReportTotalRevenueView.as_view(), name="total-revenue"),
    path("total-scan/", ReportTotalScanView.as_view(), name="total-scan"),
    path("total-click/", ReportTotalClick.as_view(), name="total-click"),
]