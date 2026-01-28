from django.urls import path

from apps.api.views import SyncDeviceView, LoginView, SetPinView, PinValidateView, ReceiptView, ReceiptSaveView

app_name = 'api'
urlpatterns = [
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("pin/set", SetPinView.as_view(), name="set-pin"),
    path("pin/validate", PinValidateView.as_view(), name="set-pin"),
    path("sync/device", SyncDeviceView.as_view(), name="sync-data"),
    path("receipt/save", ReceiptSaveView.as_view(), name="receipt-save"),
    path("receipt/<int:pk>", ReceiptView.as_view(), name="receipt"),
]