import json
import os
from os import remove, removedirs
from urllib.parse import urlparse, parse_qs

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.http import Http404, JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView

from apps.camera.models import Camera
from apps.camera.serializers import CameraRoiSerializer
from apps.camera.tasks import BAZAAR_SNAPSHOT_UPDATE_KEY, run_sync_cameras
from apps.main.models import Bazaar
from smartbozor.helpers import to_int
from smartbozor.redis import REDIS_CLIENT
from smartbozor.security import camera_signer


class CameraBazaarChoiceView(LoginRequiredMixin, TemplateView):
    template_name = 'main/bazaar-choice.j2'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["route"] = "camera:list"
        context["show_online"] = True
        context["extra"] = {
            bid: _("{0}/{1} ta kamera").format(m, n) for bid, n, m in Camera.objects.filter(
                is_active=True
            ).values(
                "bazaar_id",
            ).annotate(
                n=Count("id"),
                m=Count("id", filter=Q(is_online=True)),
            ).values_list("bazaar_id", "n", "m")
        }

        return context


class CameraListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Camera
    paginate_by = 24
    ordering = ('id', )
    permission_required = "camera.view_camera"
    template_name = 'camera/list.j2'

    def get(self, request, *args, **kwargs):
        self.set_bazaar(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(
            bazaar_id=self.bazaar.id,
            is_active=True
        ).order_by("id")

    def render_to_response(self, context, **response_kwargs):
        if self.request.user.has_perm("camera.change_camera"):
            u_ok = self.request.GET.get("u", "false") == "true"
            o_ok = self.request.GET.get("o", "false") == "true"
            remove_ok = to_int(self.request.GET.get("r", 0), 0)

            if u_ok or o_ok:
                if run_sync_cameras(self.bazaar.id, force_update=u_ok):
                    messages.success(self.request, _("Rasmlarni yangilanish boshlandi"))
                else:
                    messages.warning(self.request, _("Rasmlar yangilanish jarayonida..."))

                return redirect("camera:list", self.bazaar.id)
            elif self.request.GET.get("check", "false") == "true":
                return HttpResponse(str(self.get_updating()).lower())
            elif remove_ok > 0:
                try:
                    cam = Camera.objects.get(id=remove_ok, bazaar_id=self.bazaar.id)
                    if cam.screenshot:
                        cam.screenshot.delete()
                        cam.screenshot = None
                        cam.save()
                        messages.success(self.request, _("Screenshot muvaffaqiyatli o'chirildi."))
                finally:
                    pass

        return super().render_to_response(context, **response_kwargs)

    def set_bazaar(self, request, *args, **kwargs):
        try:
            self.bazaar = Bazaar.objects.filter(
                id__in=request.user.allowed_bazaar.values_list('id', flat=True)
            ).get(pk=kwargs['pk'])  # type: Bazaar
        except Bazaar.DoesNotExist:
            raise Http404

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bazaar"] = self.bazaar
        context["PAGE_TITLE"] = str(self.bazaar) + " » " + _("Kameralar ro'yxati")
        context["updating"] = self.get_updating()

        return context

    def get_updating(self):
        return bool(REDIS_CLIENT.exists(BAZAAR_SNAPSHOT_UPDATE_KEY.format(self.bazaar.id)))


class CameraPreview(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    TITLE = _("Kamerani ko'rish")

    model = Camera
    template_name = 'camera/preview.j2'
    permission_required = "camera.view_camera"

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] =  " » ".join([str(self.object.bazaar), str(self.object.name)])

        context["stream_host"] = os.getenv("CAMERA_STREAM_HOST")
        return context


class CameraVerifyView(View):
    def get(self, request, *args, **kwargs):
        original_uri = request.META.get("HTTP_X_ORIGINAL_URI")

        try:
            parsed = urlparse(original_uri)
            query_params = parse_qs(parsed.query)
            token = query_params.get('token', [None])[0]

            if not token:
                raise Exception(_("Token missing"))

            signed_data = camera_signer.unsign(token, max_age=30)
            resp = HttpResponse("OK")
            # Nginx `auth_request_set $upstream_http_x_device_sn` bilan oladi:
            bazaar_id, device_sn = signed_data.split(":", 1)
            bazaar = Bazaar.objects.get(id=bazaar_id)
            resp["X-Device-SN"] = device_sn
            resp["X-Server-IP"] = bazaar.server_ip
            return resp
        except Exception as e:
            if settings.DEBUG:
                raise

            return HttpResponseForbidden()


class CameraAiPreview(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    TITLE = _("Kamerani ko'rish")

    model = Camera
    template_name = 'camera/preview-ai.j2'
    permission_required = "camera.view_camera"

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get("image", "false").lower() == "true":
            camera = self.object # type: Camera
            access_token = os.environ.get("CONTROL_ACCESS_TOKEN")
            try:
                snapshot_url = f"http://{camera.bazaar.server_ip}:1984/api/ai/snapshot/{camera.device_sn}"
                response = requests.get(snapshot_url, headers={
                    "Authorization": f"Bearer {access_token}"
                }, timeout=10)
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "image/jpeg")
                return HttpResponse(response.content, content_type=content_type)
            except Exception as e:
                raise e

        return super().render_to_response(context, **response_kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] =  " » ".join([str(self.object.bazaar), str(self.object.name)])

        return context


class CameraRoiEditView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Camera
    permission_required = "camera.change_camera"
    template_name = 'camera/roi.j2'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        try:
            data = json.loads(request.body)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e)
            })

        data = CameraRoiSerializer(data=data, many=True)
        if not data.is_valid():
            return JsonResponse({
                "success": False,
                "message": "Invalida request data",
                "errors": data.errors,
            })

        try:
            for row in data.validated_data:
                if len(row['points']) != 4:
                    raise Exception(_("ROI faqat 4 ta nuqtadan iborat bo'lishi shart."))

            self.object.roi = data.data
            self.object.save()
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e)
            })

        return JsonResponse({
            "success": True,
            "message": _("Muvaffaqiyatli saqlandi"),
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["PAGE_TITLE"] =  " » ".join([str(self.object.bazaar), str(self.object.name), "Region of interest"])

        return context

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
