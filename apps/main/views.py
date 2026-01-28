import os
import subprocess

import requests
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.views.generic import TemplateView
from django_jinja.views.generic import DetailView

from apps.camera.serializers import DeviceInfo
from apps.main.models import Bazaar


ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN")


class MainIndexView(TemplateView):
    template_name = 'main/index.j2'


class MainBazaarOnline(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'main/bazaar-online.j2'
    permission_required = "main.bazaar_online"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["result"] = Bazaar.check_online(False, check_files_count=True)
        return context


class MainBazaarTestSsh(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Bazaar
    template_name = 'main/test-ssh.j2'
    permission_required = "main.bazaar_online"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        success, result, return_code, msg = self.check_ssh_and_get_time()
        context["success"] = success
        context["result"] = result
        context["return_code"] = return_code
        context["msg"] = msg

        return context

    def check_ssh_and_get_time(self):
        """
        SSH orqali ulanib, Windows vaqti olishga urunadi.
        Qaytaradi:
          (success: bool, time_iso: Optional[str], returncode: int, stderr_or_msg: str)

        success=True bo'lsa, time_iso ISO-8601 satr bo'ladi.
        """
        cmd = self._ssh_cmd()
        timeout = 15

        # Agar _ssh_cmd ichida "-N" qoldirilgan bo'lsa, unda remote command ishlamaydi.
        # Shuning uchun agar sizda -N bo'lsa, uni olib tashlang — yuqoridagi _ssh_cmd example shuni hisobga oladi.
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return False, None, -1, f"timeout after {timeout}s"
        except FileNotFoundError as exc:
            return False, None, -1, f"ssh binary not found: {exc}"
        except Exception as exc:
            return False, None, -1, f"unexpected error: {exc}"

        stdout = proc.stdout.decode(errors='ignore').strip()
        stderr = proc.stderr.decode(errors='ignore').strip()

        # Agar returncode 0 bo'lsa, stdout ichida vaqt bo'lishi kerak
        if proc.returncode == 0 and stdout:
            # stdout ga qo'shimcha chiziqlar kelsa, birinchi qatordan oling
            first_line = stdout.splitlines()[0].strip()
            return True, first_line, proc.returncode, stderr or "ok"
        else:
            # Agar PowerShell mavjud bo'lmasa yoki boshqa xatolik: stderr yoki stdoutni qaytaramiz
            # Ba'zan Windows auth xatolari stderr ga tushadi
            msg = stderr or stdout or f"ssh exited with code {proc.returncode}"
            return False, None, proc.returncode, msg

    def _ssh_cmd(self) -> list[str]:
        identity = str(settings.BASE_DIR / '.ssh' / 'id_ed25519')
        known_hosts = str(settings.BASE_DIR / '.ssh' / 'known_hosts')

        cmd = [
            "ssh",
            "-i", identity,
            "-p", str(self.object.server_port),
            "-o", "BatchMode=yes",
            "-o", "ExitOnForwardFailure=yes",
            "-o", f"UserKnownHostsFile={known_hosts}",
            "-o", "StrictHostKeyChecking=accept-new"
        ]

        cmd.append(f"{self.object.server_user}@{self.object.server_ip}")

        cmd.extend([
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "(Get-Date).ToString('o')"
        ])

        return cmd


class MainBazaarSmartBozorControl(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Bazaar
    template_name = 'main/test-sbc.j2'
    permission_required = "main.bazaar_online"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            context["version"] = requests.get(f"http://{self.object.server_ip}:1984/api/version", timeout=5).text
        except Exception as e:
            context["version"] = str(e)

        try:
            context["files_count"] = requests.get(f"http://{self.object.server_ip}:1984/api/snapshot/files/count", timeout=5).text
        except Exception as e:
            context["files_count"] = str(e)

        try:
            req = requests.get(f"http://{self.object.server_ip}:1984/api/devices", headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }, timeout=15)
            req.raise_for_status()

            context["result"] = DeviceInfo(req.json()["devices"], many=True).data
        except Exception as exc:
            context["error"] = str(exc)

        return context


class MainBazaarData(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Bazaar
    permission_required = "main.bazaar_online"

    def render_to_response(self, context, **response_kwargs):
        try:
            resp = requests.get(f"http://{self.object.server_ip}:1984/snapshot/data/{self.kwargs['path']}", headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }, timeout=10)
            resp.raise_for_status()

            return HttpResponse(resp.content, content_type=resp.headers['content-type'])
        except Exception as e:
            return HttpResponse(str(e))


class MainBazaarTestDiscovery(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Bazaar
    template_name = 'main/test-discovery.j2'
    permission_required = "main.bazaar_online"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            req = requests.get(f"http://{self.object.server_ip}:1984/api/discovery", headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }, timeout=10)

            if req.status_code == 200:
                context["result"] = req.text
            else:
                context["error"] = req.text
        except Exception as exc:
            context["error"] = str(exc)

        return context


class MainBazaarRunSnapshot(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Bazaar
    template_name = 'main/test-run-snapshot.j2'
    permission_required = "main.bazaar_online"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            req = requests.get(f"http://{self.object.server_ip}:1984/api/run-snapshot", headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }, timeout=10)

            context["result"] = req.json()
        except Exception as exc:
            context["error"] = str(exc)

        return context
