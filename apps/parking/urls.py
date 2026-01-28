from django.urls import path

from apps.parking.views import ParkingBazaarChoiceView, ParkingStatusListView

app_name = "parking"
urlpatterns = [
    path("list/", ParkingBazaarChoiceView.as_view(), name="list-bazaar"),
    path("list/<int:pk>/", ParkingStatusListView.as_view(), name="list"),
]
