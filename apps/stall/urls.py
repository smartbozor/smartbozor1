from django.urls import path

from apps.stall.views import StallListView, StallQrCode, StallBazaarChoiceView, StallImportView

app_name = "stall"
urlpatterns = [
    path("list/", StallBazaarChoiceView.as_view(), name="list-bazaar"),
    path("list/<int:pk>/", StallListView.as_view(), name="list"),
    path("import/<int:pk>/", StallImportView.as_view(), name="import"),
    path("qr-code/<int:pk>/", StallQrCode.as_view(), name="qr-code")
]
