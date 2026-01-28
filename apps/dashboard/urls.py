from django.urls import path

from apps.dashboard.views import DashboardIndexView

app_name = 'dashboard'

urlpatterns = [
    path("", DashboardIndexView.as_view(), name="index"),
    path("<int:pk>/", DashboardIndexView.as_view(), name="index-bazaar"),
]
