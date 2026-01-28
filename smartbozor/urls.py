"""
URL configuration for smartbozor project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.utils.translation import gettext_lazy as _
from django.views.i18n import JavaScriptCatalog
from django_otp.admin import OTPAdminSite

from apps.parking.views import ParkingActionView
from apps.payment.views import PaymentQrStallView, PaymentClick, PaymentPayme, PaymentQrShopView, PaymentQrRentView, \
    PaymentQrParkingView, PaymentQrPoint, PaymentClickPointProduct
from smartbozor.storages import stall_storage

urlpatterns = [
    path('control/', admin.site.urls),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("api/", include("apps.api.urls")),

    path("s/<int:bazaar_id>-<int:area_id>-<int:section_id>-<str:number>/", PaymentQrStallView.as_view(), name="stall-qr"),
    path("m/<int:bazaar_id>-<int:area_id>-<int:section_id>-<str:number>/", PaymentQrShopView.as_view(), name="shop-qr"),
    path("r/<int:bazaar_id>-<int:thing_id>-<int:number>/", PaymentQrRentView.as_view(), name="thing-qr"),
    path("p/<int:pk>/", PaymentQrParkingView.as_view(), name="parking-qr"),
    path("x/<int:pk>/", PaymentQrPoint.as_view(), name="point-qr"),

    path("parking/<str:action>/<str:token>/", ParkingActionView.as_view(), name="action"),

    path("payment/click/<str:name>/", PaymentClick.as_view(), name="payment-click"),
    path("payment/click/x/<str:slug>/", PaymentClickPointProduct.as_view(), name="payment-x-click"),
    path("payment/payme/<str:name>/", PaymentPayme.as_view(), name="payment-payme"),
]

if settings.DEBUG:
    urlpatterns += debug_toolbar_urls()
    urlpatterns += static(stall_storage.base_url, document_root=stall_storage.location)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


urlpatterns += i18n_patterns(
    path("", include( "apps.main.urls")),

    path("ai/", include("apps.ai.urls")),
    path("payment/", include("apps.payment.urls")),
    path("dashboard/", include( "apps.dashboard.urls")),
    path("account/", include( "apps.account.urls")),
    path("stall/", include( "apps.stall.urls")),
    path("shop/", include( "apps.shop.urls")),
    path("report/", include( "apps.report.urls")),
    path("parking/", include( "apps.parking.urls")),
    path("rent/", include( "apps.rent.urls")),
    path("camera/", include( "apps.camera.urls")),
)


admin.site.index_title = _('Smart bozor')
admin.site.site_header = _('Smart bozor')
admin.site.site_title = _('Smart bozor management')

if not settings.DEBUG:
    admin.site.__class__ = OTPAdminSite
