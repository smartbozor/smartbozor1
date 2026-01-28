import json
import os
import subprocess
import time
from datetime import timedelta, datetime

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, F
from django.db.models.functions import Mod
from django.http import JsonResponse
from django.shortcuts import redirect, resolve_url
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView, DetailView

from apps.ai.models import StallDataSet
from apps.ai.serializers import StallMarkSerializer, StallMarkModerateSerializer
from apps.camera.models import Camera
from apps.main.models import Bazaar
from smartbozor.helpers import to_int


class StallMarkBazaarChoiceView(LoginRequiredMixin, TemplateView):
    FILTER_STATUS = StallDataSet.STATUS_NEW
    template_name = 'main/bazaar-choice.j2'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        snapshot_after = StallDataSet.get_snapshot_after()

        qs = StallDataSet.objects.filter(
            snapshot_at__gte=snapshot_after,
        ).values(
            "bazaar_id",
        ).annotate(
            n=Count("id")
        )

        if self.FILTER_STATUS is not None:
            if isinstance(self.FILTER_STATUS, list):
                qs = qs.filter(status__in=self.FILTER_STATUS)
            else:
                qs = qs.filter(status=self.FILTER_STATUS)

        context["route"] = "ai:stall-mark"
        context["extra"] = {
            bid: _("{0} ta yangi").format(n) for bid, n in qs.values_list("bazaar_id", "n")
        }

        return context


class StallMarkModerateBazaarChoiceView(StallMarkBazaarChoiceView):
    FILTER_STATUS = StallDataSet.STATUS_MARKED

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["route"] = "ai:stall-mark-moderate"
        return context


class StallMarkUpdateBazaarChoiceView(StallMarkBazaarChoiceView):
    FILTER_STATUS = [
        StallDataSet.STATUS_MARKED_MODERATED,
        StallDataSet.STATUS_GENERATED,
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["route"] = "ai:stall-mark-update"
        return context


class StallMarkView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    TITLE = _("Rastla bandligini belgilash")
    FILTER_STATUS = StallDataSet.STATUS_NEW

    model = Bazaar
    template_name = 'ai/stall-mark.j2'
    permission_required = 'ai.change_stalldataset'

    def render_to_response(self, context, **response_kwargs):
        wrong = to_int(self.request.GET.get("wrong", 0), 0)
        group = to_int(self.request.GET.get("group", 0), 0)
        camera = to_int(self.request.GET.get("camera", 0), 0)
        next_id = to_int(self.request.GET.get("next", 0), 0)
        if wrong > 0:
            to_url, status = "ai:stall-mark", [StallDataSet.STATUS_NEW]
            if next_id > 0:
                to_url, status = "ai:stall-mark-update", [StallDataSet.STATUS_MARKED_MODERATED, StallDataSet.STATUS_GENERATED]

            StallDataSet.objects.filter(id=wrong, status__in=status).update(
                status=StallDataSet.STATUS_WRONG
            )

            return redirect(resolve_url(to_url, self.object.id) + f"?group={group}&camera={camera}&next={next_id}")

        return super().render_to_response(context, **response_kwargs)

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e)
            })

        data = StallMarkSerializer(data=data)
        if not data.is_valid():
            return JsonResponse({
                "success": False,
                "message": "Invalida request data",
                "errors": data.errors,
            })

        try:
            with transaction.atomic():
                dataset = StallDataSet.objects.select_for_update().get(id=data.validated_data["id"])
                if dataset.status != StallDataSet.STATUS_NEW:
                    raise Exception("Status was changed")

                dataset.status = StallDataSet.STATUS_MARKED
                dataset.data = data.validated_data["data"]
                dataset.save()
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e),
            })

        return JsonResponse({
            "success": True,
            "message": "Successfully saved"
        })

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        group = to_int(self.request.GET.get("group", 0), 0)
        camera_id = to_int(self.request.GET.get("camera", 0), 0)
        next_id = to_int(self.request.GET.get("next", 0), 0)
        snapshot_after = StallDataSet.get_snapshot_after()

        filter_status = self.FILTER_STATUS
        if not isinstance(filter_status, list):
            filter_status = [filter_status]

        qs = StallDataSet.objects.filter(
            bazaar__id=self.object.id,
            status__in=filter_status,
            snapshot_at__gte=snapshot_after,
        ).order_by('id').annotate(
            g=Mod(F('id'), 10) + 1
        )

        if next_id > 0:
            qs = qs.filter(id__gt=next_id)

        context['group_total'] = {g: n for g, n in qs.all().order_by().values("g").annotate(
            n=Count("id")
        ).values_list("g", "n")}
        context['camera_total'] = {k: v for k, v in qs.all().order_by().values("camera_id").annotate(
            n=Count("id")
        ).values_list("camera_id", "n")}

        if 0 < group <= 10:
            qs = qs.filter(g=group)

        if camera_id > 0:
            qs = qs.filter(camera_id=camera_id)

        found = qs.first()

        context["found"] = found
        context["group"] = group
        context["camera_id"] = camera_id
        context["cameras"] = Camera.objects.filter(bazaar=self.object).order_by("id")

        if found:
            context["PAGE_TITLE"] = " » ".join([str(found.bazaar), str(found.camera.name), str(self.TITLE)])
        else:
            context["PAGE_TITLE"] = str(self.TITLE)

        return context

    def get_queryset(self):
        return super().get_queryset().filter(
            id__in=self.request.user.allowed_bazaar.values_list('id', flat=True)
        )


class StallMarkModerateView(StallMarkView):
    TITLE = _("Rasta bandligini tekshirish")
    FILTER_STATUS = StallDataSet.STATUS_MARKED

    def post(self, request, *args, **kwargs):
        try:
            data = StallMarkModerateSerializer(data=json.loads(request.body))
            if not data.is_valid():
                return JsonResponse({
                    "success": False,
                    "message": "Invalida request data",
                    "errors": data.errors,
                })

            with transaction.atomic():
                dataset = StallDataSet.objects.select_for_update().get(id=data.validated_data["id"])
                if dataset.status != self.FILTER_STATUS:
                    raise Exception("Status was changed")

                dataset.status = StallDataSet.STATUS_MARKED_MODERATED if data.validated_data[
                    "data"] else StallDataSet.STATUS_NEW
                dataset.save()

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e)
            })

        return JsonResponse({
            "success": True,
            "message": "Successfully saved"
        })


class StallMarkUpdateView(StallMarkView):
    TITLE = _("Rastani bandligini tahrirlash")
    FILTER_STATUS = [
        StallDataSet.STATUS_GENERATED,
        StallDataSet.STATUS_MARKED_MODERATED
    ]

    def post(self, request, *args, **kwargs):
        try:
            data = StallMarkSerializer(data=json.loads(request.body))
            if not data.is_valid():
                return JsonResponse({
                    "success": False,
                    "message": "Invalida request data",
                    "errors": data.errors,
                })

            with transaction.atomic():
                dataset = StallDataSet.objects.select_for_update().get(id=data.validated_data["id"])
                if dataset.status not in self.FILTER_STATUS:
                    raise Exception("Status was changed")

                if dataset.status == dataset.STATUS_GENERATED:
                    dataset.status = StallDataSet.STATUS_MARKED_MODERATED

                dataset.data = data.validated_data["data"]
                dataset.save()

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e)
            })

        return JsonResponse({
            "success": True,
            "message": "Successfully saved"
        })


class StallAiTestBazaar(StallMarkBazaarChoiceView):
    FILTER_STATUS = [
        StallDataSet.STATUS_WRONG,
        StallDataSet.STATUS_NEW,
        StallDataSet.STATUS_MARKED,
        StallDataSet.STATUS_MARKED_MODERATED,
        StallDataSet.STATUS_GENERATED,
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["route"] = "ai:stall-test"
        return context


class StallAiTest(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    TITLE = _("Rastla bandligini AI orqali tekshirish ")

    model = Bazaar
    template_name = 'ai/stall-test.j2'
    permission_required = 'ai.change_stalldataset'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["status_total"] = {k: v for k, v in StallDataSet.objects.filter(
            status__in=StallAiTestBazaar.FILTER_STATUS
        ).values("status").annotate(
            n=Count("id")
        ).values_list("status", "n")}

        camera_id = to_int(self.request.GET.get("camera", 0), 0)
        current_id = to_int(self.request.GET.get("id", 0))
        status = to_int(self.request.GET.get("status", -2))

        qs = StallDataSet.objects.filter(
            status__in=StallAiTestBazaar.FILTER_STATUS,
            id__gt=current_id
        ).order_by("id")

        if status >= -1:
            qs = qs.filter(status=status)

        if camera_id > 0:
            qs = qs.filter(camera_id=camera_id)

        context['camera_total'] = {k: v for k, v in qs.all().order_by().values("camera_id").annotate(
            n=Count("id")
        ).values_list("camera_id", "n")}

        found = qs.first()

        context["status"] = status
        context["found"] = found
        context["ms"] = int(time.time() * 1000)
        context["camera_id"] = camera_id
        context["cameras"] = Camera.objects.filter(bazaar=self.object).order_by("id")

        if found and found.camera and found.camera.roi:
            if not isinstance(found.data, list):
                found.data = []

            render_data = {
                "file": found.image.path,
                "image": True,
                "rois": found.camera.roi,
                "occupied": found.data,
            }

            aigen_app = os.getenv("AIGEN_APP")
            workdir = os.path.dirname(aigen_app)
            args = [aigen_app]
            args.extend([
                "--render",
                json.dumps(render_data)
            ])

            if "print_args" in self.request.GET:
                print(args)

            result = subprocess.run(
                args,
                cwd=workdir,
                capture_output=True,
                text=True,
            )

            if "print_stdout" in self.request.GET:
                print(result.stdout)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                context["render_image"] = data["image"]
            else:
                messages.error(self.request, result.stdout)

        return context
