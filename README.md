# smartbozor
Smart bozor


# Run SQL
```bash
docker run --net dev --rm -e CLICKHOUSE_PASSWORD=default -p 8123:8123 clickhouse/clickhouse-server:latest-alpine
```


# Run CELERY
```bash
celery -A smartbozor worker --time-limit=0 --soft-time-limit=0 -l INFO
```

# Run RTSP 
```bash
ffmpeg -re -stream_loop -1 -framerate 1 \
  -i "/Users/shranet/projects/data/frames/stall_%05d.jpg" \
  -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
  -f rtsp -rtsp_transport tcp "rtsp://127.0.0.1:8554/Streaming/Channels/101"
```


# Example MENU
```python
menu = [{
    "id": 1,
    "title": _("Rasta"),
    "form": [{
        "type": "header",
        "label": _("Rasta uchun to'lov"),
        "help": "askjdahskj hasdjkfh jkasdhfjk asdfj hadjksfh ajksdfhkja sdhkfj"
    }, {
        "type": "text",
        "name": "stall",
        "label": _("Rasta raqami"),
        "regex": Stall.NUMBER_PATTERN,
        "help": _("💡Rasta raqami kichik lotin harflari va raqamlardan iborat bo'lishi lozim.")
    }, {
        "type": "dropdown",
        "name": "stall2",
        "label": _("Rasta raqami"),
        "items": [
            {"id": 1, "label": "Toshkent"},
            {"id": 2, "label": "Samarqand 2"},
            {"id": 22, "label": "Samarqand 22"},
            {"id": 3, "label": "Buxoro"},
            {"id": 4, "label": "Farg'ona"},
            {"id": 5, "label": "Namangan"},
            {"id": 6, "label": "Andijon"}
        ],
        "help": _("💡Rasta raqami kichik lotin harflari va raqamlardan iborat bo'lishi lozim.")
    }, {
        "type": "currency",
        "name": "amount",
        "label": _("To'lov summasi"),
        "min": 1000,
        "max": 100_000,
        "help": _("💡Rasta raqami kichik lotin harflari va raqamlardan iborat bo'lishi lozim.")
    }, {
        "type": "button",
        "label": _("To'lash"),
    }]
}, {
    "id": 2,
    "title": _("Do'kon"),
    "form": [{
        "type": "header",
        "label": _("Do'kon uchun to'lov"),
    }, {
        "type": "text",
        "name": "shop",
        "label": _("Do'kon raqami"),
        "regex": Shop.NUMBER_PATTERN,
    }, {
        "type": "currency",
        "name": "amount",
        "label": _("To'lov summasi"),
        "min": 1000,
        "max": 10_000_000
    }, {
        "type": "button",
        "label": _("To'lash"),
    }]
}, {
    "id": 3,
    "title": _("Avtoturargoh"),
    "form": [{
        "type": "header",
        "label": _("Avtoturargoh uchun to'lov"),
    }, {
        "type": "currency",
        "name": "amount",
        "label": _("Narxi"),
        "readonly": True,
        "value": 4000
    }, {
        "type": "button",
        "label": _("To'lash"),
    }]
}, {
    "id": 4,
    "title": _("Tarozi4"),
    "form": [{
        "type": "header",
        "label": _("Tarozi uchun to'lov"),
    }, {
        "type": "currency",
        "name": "amount",
        "label": _("Tarozi ijara narxi"),
        "readonly": True,
        "value": 5000
    }, {
        "type": "button",
        "label": _("To'lash"),
    }]
}, {
    "id": 5,
    "title": _("Molbozor"),
    "form": [{
        "type": "header",
        "label": _("Chorva uchun to'lov"),
    }, {
        "type": "radio",
        "name": "type",
        "label": _("Chorva turi"),
        "items": [
            {"id": 1, "label": _("Kichik - 20 000 so'm")},
            {"id": 2, "label": _("O'rta - 30 000 so'm")},
            {"id": 3, "label": _("Katta - 50 000 so'm")},
        ]
    }, {
        "type": "button",
        "label": _("To'lash"),
    }]
}]
```
