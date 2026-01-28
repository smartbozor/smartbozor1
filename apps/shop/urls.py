from django.urls import path
from apps.shop.views import ShopListView, ShopQrCode, ShopImportView, ShopBazaarChoiceView

app_name = "shop"
urlpatterns = [
    path("list/", ShopBazaarChoiceView.as_view(), name="list-bazaar"),
    path("list/<int:pk>/", ShopListView.as_view(), name="list"),
    path("qr-code/<int:pk>/", ShopQrCode.as_view(), name="qr-code"),
    path("import/<int:pk>/", ShopImportView.as_view(), name="import"),
]
