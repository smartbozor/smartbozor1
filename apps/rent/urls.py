from django.urls import path

from apps.rent.views import RentListView, RentQrCode, RentBazaarChoice

app_name = "rent"
urlpatterns = [
    path("list/<int:pk>/", RentBazaarChoice.as_view(), name="list-bazaar"),
    path("list/<int:bazaar_id>-<int:pk>/", RentListView.as_view(), name="list"),
    path("qr-code/<int:bazaar_id>-<int:thing_id>-<int:number>/", RentQrCode.as_view(), name="qr-code"),
]
