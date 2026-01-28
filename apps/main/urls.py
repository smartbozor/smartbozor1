from django.urls import path, re_path

from apps.main.views import MainIndexView, MainBazaarOnline, MainBazaarTestSsh, MainBazaarSmartBozorControl, \
    MainBazaarData, MainBazaarTestDiscovery, MainBazaarRunSnapshot

app_name = 'main'

urlpatterns = [
    path("", MainIndexView.as_view(), name="index"),
    path("bazaar/online/", MainBazaarOnline.as_view(), name="bazaar-online"),
    path("bazaar/test-ssh/<int:pk>/", MainBazaarTestSsh.as_view(), name="bazaar-test-ssh"),
    path("bazaar/test-sbc/<int:pk>/", MainBazaarSmartBozorControl.as_view(), name="bazaar-test-sbc"),
    path("bazaar/test-discovery/<int:pk>/", MainBazaarTestDiscovery.as_view(), name="bazaar-test-discovery"),
    path("bazaar/test-run-snapshot/<int:pk>/", MainBazaarRunSnapshot.as_view(), name="bazaar-test-run-snapshot"),
    re_path(r"bazaar/(?P<pk>\d+)/data/(?P<path>.*)", MainBazaarData.as_view(), name="bazaar-data"),
]