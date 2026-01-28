import re
import threading

from apps.parking.models import ParkingWhitelist
from apps.parking.signals import CACHE_VERSION_KEY
from smartbozor.redis import REDIS_CLIENT

_lock = threading.RLock()
_local_compiled = {
    "version": None,
    "items": None,
}


def _load_patterns_from_db():
    return list(ParkingWhitelist.objects.order_by("id").all())

def get_compiled_whitelist():
    global _local_compiled
    version = int(REDIS_CLIENT.get(CACHE_VERSION_KEY) or 1)

    if _local_compiled["version"] == version and _local_compiled["items"] is not None:
        return _local_compiled["items"]

    # Slow path: lock bilan tekshir/yangila
    with _lock:
        # boshqa thread allaqachon yangilagan bo‘lishi mumkin
        if _local_compiled["version"] == version and _local_compiled["items"] is not None:
            return _local_compiled["items"]

        rows = _load_patterns_from_db()

        compiled = []
        for row in rows:
            try:
                c = re.compile(row.pattern, re.IGNORECASE)
                compiled.append((row.region_id, row.district_id, row.bazaar_id, c))
            except re.error:
                # noto‘g‘ri regex bo‘lsa, log qilib tashlab ketamiz
                # logger.warning("Invalid regex in ParkingWhitekist id=%s", _id)
                continue

        _local_compiled["version"] = version
        _local_compiled["items"] = compiled
        return compiled

