import datetime
import json
import os
from contextlib import ExitStack

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.camera.models import Camera
from apps.camera.serializers import DeviceInfo
from apps.main.models import Bazaar
from smartbozor.celery import app
from smartbozor.redis import REDIS_CLIENT

ACCESS_TOKEN = os.environ.get("CONTROL_ACCESS_TOKEN")
CAMERA_INFO_KEY = "camera_task:{}"
BAZAAR_SNAPSHOT_UPDATE_KEY = "bazaar_snapshot_update:{}"


def calc_countdown():
    now_t = timezone.now()
    if now_t.hour >= 15:
        countdown = int((now_t.replace(hour=6, minute=0, second=0, microsecond=0) + datetime.timedelta(
            days=1) - now_t).total_seconds())
    elif now_t.hour < 6:
        countdown = int((now_t.replace(hour=6, minute=0, second=0, microsecond=0) - now_t).total_seconds())
    else:
        countdown = 10 if settings.DEBUG else 600

    return countdown


def run_update_camera_info(camera_id):
    res = update_camera_info.apply_async(kwargs={'camera_id': camera_id})

    key = CAMERA_INFO_KEY.format(camera_id)
    old_task_id = REDIS_CLIENT.getset(key, res.id)

    if old_task_id and old_task_id.decode() != res.id:
        app.control.revoke(old_task_id.decode(), terminate=True)

    REDIS_CLIENT.expire(key, 7 * 24 * 3600)
    return res


@app.task(bind=True, ignore_result=True, max_retries=None)
def update_camera_info(self, camera_id, started_at=None):
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

    if started_at is None:
        started_at = now

    if now - started_at > 7 * 24 * 3600:
        print(f"{camera_id}: timeout")
        return

    try:
        camera = Camera.objects.get(pk=camera_id)

        if camera.device_sn and camera.bazaar.server_ip and camera.bazaar.server_user and camera.bazaar.app_version != '-':
            print(f"update: cam={camera.id}")
            rois = []
            if isinstance(camera.roi, list):
                rois = camera.roi

            data = {
                camera.device_sn: {
                    "ip": camera.camera_ip,
                    "port": camera.camera_port,
                    "username": camera.username,
                    "password": camera.password,
                    "stream_port": camera.camera_port,
                    "rois": rois,
                    "use_ai": camera.use_ai,
                }
            }

            url = f"http://{camera.bazaar.server_ip}:1984/api/update-devices"
            print(f"\tpost: {url}")
            print(f"\tdata: {json.dumps(data)}")

            resp = requests.post(url, json=data, headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }, timeout=15)

            if resp.status_code == 200:
                print(f"\t{resp.text}")
            else:
                print(f"\tstatus={resp.status_code}")
    except Camera.DoesNotExist:
        print(f"\tcamera not found")
    except Exception as e:
        print(f"\terror={e}")
        raise self.retry(exc=e, countdown=calc_countdown(), kwargs={
            'camera_id': camera_id,
            'started_at': started_at,
        })


def run_sync_cameras(bazaar_id, force_update=False):
    key = BAZAAR_SNAPSHOT_UPDATE_KEY.format(bazaar_id)
    result = REDIS_CLIENT.set(key, "-", nx=True, ex=3600)
    if not result:
        return False

    sync_cameras.apply_async(kwargs={
        'bazaar_id': bazaar_id,
        'force_update': force_update,
        'clear_redis_key': True
    })

    return True


@app.task(ignore_result=True, max_retries=None)
def sync_cameras(bazaar_id, force_update=False, clear_redis_key=False):
    def remove_key():
        if clear_redis_key:
            key = BAZAAR_SNAPSHOT_UPDATE_KEY.format(bazaar_id)
            REDIS_CLIENT.delete(key)

    with ExitStack() as stack:
        stack.callback(remove_key)

        with transaction.atomic():
            try:
                bazaar = Bazaar.objects.select_for_update().get(pk=bazaar_id)
            except Exception as e:
                print(f"{bazaar_id}: {e}")
                return

            host = f"http://{bazaar.server_ip}:1984"
            url = f"{host}/api/devices"

            try:
                data = DeviceInfo(requests.get(url, timeout=5, headers={
                    "Authorization": f"Bearer {ACCESS_TOKEN}"
                }).json()["devices"], many=True).data
            except Exception as e:
                print("Error: " + str(e))
                Camera.objects.filter(bazaar_id=bazaar.id).update(is_online=False)
                return

            camera_by_device_sn, camera_by_mac, camera_by_ip, camera_empty = dict(), dict(), dict(), []
            camera_set = list(bazaar.camera_set.order_by('id').all())
            n, found_ids = len(camera_set), set([row.id for row in camera_set])

            update_cameras = dict()
            for cam in camera_set:
                if cam.device_sn:
                    camera_by_device_sn[cam.device_sn] = cam
                    update_cameras[cam.device_sn] = cam.id
                    continue

                if cam.camera_mac:
                    camera_by_mac[cam.camera_mac] = cam
                    continue

                if cam.camera_ip:
                    camera_by_ip[cam.camera_ip] = cam
                    continue

                camera_empty.append(cam)

            new_devices = []
            for dev in data:
                sn, mac, ip = dev["device_sn"], dev["mac"], dev["ip"]
                print(f"\t{ip}...")

                if sn in camera_by_device_sn:
                    cam = camera_by_device_sn[sn]
                    del update_cameras[cam.device_sn]
                elif mac in camera_by_mac:
                    cam = camera_by_mac[mac]
                elif ip in camera_by_ip:
                    cam = camera_by_ip[ip]
                elif camera_empty:
                    cam = camera_empty.pop(0)
                else:
                    cam = Camera(
                        bazaar_id=bazaar.id,
                        device_sn=sn,
                        name=f"Camera {n}",
                        camera_mac=mac,
                        camera_ip=ip,
                        username="admin",
                        password="A112233a",
                        is_online=dev["is_online"],
                    )

                    camera_set.append(cam)
                    new_devices.append(cam)
                    n += 1
                    continue

                cam.device_sn = sn
                cam.camera_mac = mac
                cam.camera_ip = ip
                cam.is_online = dev["is_online"]
                cam.save()

                found_ids.remove(cam.id)

            if new_devices:
                Camera.objects.bulk_create(new_devices, batch_size=10)

            if found_ids:
                for cam in camera_set:
                    if cam.id in found_ids:
                        cam.is_online = False

            print(f"Update camera count: {len(update_cameras)}")
            for cam_id in update_cameras.values():
                run_update_camera_info(cam_id)

            for cam in camera_set:
                snapshot_url = f"{host}/api/snapshot/{cam.device_sn}"
                status = "ONLINE" if cam.is_online else "OFFLINE"
                print(f"bazaar[{bazaar.id}]: [{status}] save snapshot {cam.id}: force={force_update}")
                save_screenshot(cam, snapshot_url, force_update)
                cam.save()


def save_screenshot(cam, snapshot_url, force_update):
    if not cam.device_sn:
        return False

    try:
        upload_to = Camera._meta.get_field('screenshot').upload_to

        subpath = os.path.join(upload_to, str(cam.bazaar_id), str(cam.id) + ".jpg")

        file_path = os.path.join(settings.MEDIA_ROOT, str(subpath))
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if not os.path.exists(file_path) or force_update:
            response = requests.get(snapshot_url, headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}"
            }, timeout=10)

            if response.status_code == 200:
                file_path_tmp = file_path + ".tmp"
                print(f"\tsave file: {file_path_tmp}")
                with open(file_path_tmp, 'wb') as f:
                    f.write(response.content)

                if os.path.getsize(file_path_tmp) > 1000:
                    print(f"\trename: from={file_path_tmp} to={file_path}")
                    os.rename(file_path_tmp, file_path)
                else:
                    print("\terror file size. remove tmp file")
                    os.remove(file_path_tmp)
                    subpath = None
            else:
                print(f"\tstatus error: {response.status_code}")
                subpath = cam.screenshot.name

        if os.path.exists(file_path) and os.path.getsize(file_path) < 1000:
            os.remove(file_path)
            print(f"\twrong file size: remove")
            subpath = None

        cam.screenshot.name = subpath
        print("\tok")
        return True
    except Exception as e:
        print(f"\terror: {e}")

    return False
