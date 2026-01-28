//ai-stall-mark.js da ham o'zgarishi kerak, agar o'zgarsa
const CANVAS_SIZE = {w: 1024, h: 576}
const JSON_ROI_SIZE = {w: 640, h: 360}
const CENTER = {x: CANVAS_SIZE.w / 2, y: CANVAS_SIZE.h / 2}
const POLY_DEFAULT_SIZE = 200
const SELECTED_FILL = 'rgba(255,235,59,0.75)';
const TRANSPARENT = 'rgba(255,235,59,0.5)';
const ICONS_URL = [
    "https://icons.getbootstrap.com/assets/icons/x-circle-fill.svg",
    "https://icons.getbootstrap.com/assets/icons/plus-circle.svg"
]
let roiJsonFiles = [];
let roiJsonIndex = -1

const save_el = document.querySelector("#id_saved")
const roi_json_el = document.querySelector("#id_json_roi")
let loading_el = document.querySelector("#id_loading")
const assign_modal_el = document.querySelector("#id_assign_modal")
const assign_modal = new bootstrap.Modal(assign_modal_el)

const canvas_el = document.querySelector("#id-camera-roi");
const canvas = new fabric.Canvas(canvas_el, {
    width: CANVAS_SIZE.w,
    height: CANVAS_SIZE.h
});

const ICONS = {};
let savedPolygons = [];

async function load_saved() {
    if (!save_el) {
        return;
    }

    const save = JSON.parse(save_el.innerText);
    if (!Array.isArray(save)) {
        return
    }

    add_saved(save)
}

function add_saved(save) {
    save.forEach(pd => {
        const label = document.querySelector(`button[data-type="${pd.type}"]`).dataset.label;
        const points = pd.points.map(p => ({
            x: parseInt(CANVAS_SIZE.w * p.x / 100000),
            y: parseInt(CANVAS_SIZE.h * p.y / 100000),
        }))
        const center = {
            left: Math.min(...points.map(p => p.x)),
            top: Math.min(...points.map(p => p.y)),
        }
        poly_add(pd.id, pd.type, label, pd.value, points, center, false);
    })
}

async function init_icons() {
    const responses = await Promise.all(
        ICONS_URL.map(url => fetch(url).then(res => res.text()))
    );

    responses.forEach((svgText, i) => {
        const url = ICONS_URL[i];
        const fileName = url.split("/").pop().replace(".svg", "");

        const encoded = encodeURIComponent(svgText)
            .replace(/'/g, "%27")
            .replace(/"/g, "%22");

        const img = document.createElement("img");
        img.src = `data:image/svg+xml,${encoded}`;
        ICONS[fileName] = img
    });

    await load_saved();
    loading_el.nextElementSibling.classList.remove("d-none")
    loading_el.remove();
    loading_el = null
}

function update_polygon_fills() {
    const active = canvas.getActiveObject();
    const selectedPolys = new Set();

    if (active) {
        if (active.type === 'polygon') {
            selectedPolys.add(active);
        } else if (active.type === 'activeSelection') {
            active.getObjects().forEach(o => {
                if (o.type === 'polygon') selectedPolys.add(o);
            });
        }
    }

    canvas.getObjects('polygon').forEach(poly => {
        const is_selected = selectedPolys.has(poly);
        if (!is_selected && poly._editing) {
            poly._toggle_editing();
        }
        poly.set('fill', is_selected ? SELECTED_FILL : TRANSPARENT);
    });

    canvas.requestRenderAll();
}

canvas.on('selection:created', update_polygon_fills);
canvas.on('selection:updated', update_polygon_fills);
canvas.on('selection:cleared', update_polygon_fills);


function remove_nearest_point(poly, pointer) {
    const pts = poly.points;
    if (!pts || pts.length === 0) return;

    if (pts.length <= 3) return;

    const m = poly.calcTransformMatrix();

    let nearestIdx = -1;
    let bestDist2 = Infinity;

    for (let i = 0; i < pts.length; i++) {
        const gp = fabric.util.transformPoint(
            new fabric.Point(pts[i].x - poly.pathOffset.x, pts[i].y - poly.pathOffset.y),
            m
        );

        const dx = gp.x - pointer.x;
        const dy = gp.y - pointer.y;
        const d2 = dx * dx + dy * dy;

        if (d2 < bestDist2) {
            bestDist2 = d2;
            nearestIdx = i;
        }
    }

    if (nearestIdx < 0) return;

    pts.splice(nearestIdx, 1);

    poly.set({
        points: pts,
        controls: fabric.controlsUtils.createPolyControls(poly)
    });

    poly.setCoords();
    canvas.requestRenderAll();
}

function index_of_longest_edge(points) {
    const n = points.length;
    if (n < 2) return -1;
    let maxLen2 = -1;
    let maxIdx = 0;
    for (let i = 0; i < n; i++) {
        const j = (i + 1) % n;
        const dx = points[j].x - points[i].x;
        const dy = points[j].y - points[i].y;
        const len2 = dx * dx + dy * dy;
        if (len2 > maxLen2) {
            maxLen2 = len2;
            maxIdx = i;
        }
    }
    return maxIdx;
}

function add_point_on_longest_edge(poly) {
    const pts = poly.points;
    if (!pts || pts.length < 2) return;

    const i = index_of_longest_edge(pts);
    if (i < 0) return;

    const j = (i + 1) % pts.length;
    const mid = {
        x: (pts[i].x + pts[j].x) / 2,
        y: (pts[i].y + pts[j].y) / 2,
    };

    pts.splice(j, 0, mid);

    poly.set({
        controls: fabric.controlsUtils.createPolyControls(poly)
    });

    poly.setCoords();
    canvas.requestRenderAll();
}

function render_icon(icon) {
    return function (ctx, left, top, _styleOverride, fabricObject) {
        const size = this.cornerSize;
        ctx.save();
        ctx.translate(left, top);
        ctx.rotate(fabric.util.degreesToRadians(fabricObject.angle));
        ctx.drawImage(icon, -size / 2, -size / 2, size, size);
        ctx.restore();
    };
}

function delete_object(_eventData, transform) {
    if (confirm(gettext("Haqiqatda o'chirishni xohlaysizmi? Agar AI uchun rasmlar belgilangan bo'lsa, o'chirish mumkin emas."))) {
        const canvas = transform.target.canvas;
        canvas.remove(transform.target);
        canvas.requestRenderAll();
    }
}

function assign_id(poly) {
    assign_modal.show()
}

function poly_add(id, type, label, value = "", points = null, center = null, focus = true) {
    if (!points) {
        points = [
            {x: 0, y: 0},
            {x: POLY_DEFAULT_SIZE, y: 0},
            {x: POLY_DEFAULT_SIZE, y: POLY_DEFAULT_SIZE},
            {x: 0, y: POLY_DEFAULT_SIZE},
        ]
    }

    if (!center) {
        center = {
            left: CENTER.x - POLY_DEFAULT_SIZE / 2,
            top: CENTER.y - POLY_DEFAULT_SIZE / 2,
        }
    }

    const poly = new fabric.Polygon(points, {
        left: center.left,
        top: center.top,
        fill: TRANSPARENT,
        strokeWidth: 3,
        stroke: 'grey',
        objectCaching: false,
        transparentCorners: false,
        cornerColor: 'blue',
    });

    poly._id = id || crypto.randomUUID();
    poly._editing = true;
    poly._type = type;
    poly._label = label;
    poly._value = value;

    poly._toggle_editing = function () {
        poly._editing = !poly._editing;
        if (poly._editing) {
            poly.cornerStyle = 'circle';
            poly.cornerColor = 'rgba(0,0,255,0.5)';
            poly.hasBorders = false;
            poly.controls = fabric.controlsUtils.createPolyControls(poly);
        } else {
            poly.cornerColor = 'blue';
            poly.cornerStyle = 'rect';
            poly.hasBorders = true;
            poly.controls = fabric.controlsUtils.createObjectDefaultControls();

            poly.controls.deleteControl = new fabric.Control({
                x: 0.5,
                y: -0.5,
                offsetY: -16,
                offsetX: 16,
                cursorStyle: 'pointer',
                mouseUpHandler: delete_object,
                render: render_icon(ICONS["x-circle-fill"]),
                cornerSize: 24,
            });

            poly.controls.assignControl = new fabric.Control({
                x: 0.5,
                y: -0.5,
                offsetY: 16,
                offsetX: 16,
                cursorStyle: 'pointer',
                mouseUpHandler: function (_ed, t) {
                    assign_id(t.target)
                },
                render: render_icon(ICONS["plus-circle"]),
                cornerSize: 24,
            });
        }
        poly.setCoords();
    }
    poly._toggle_editing()

    poly._render_super = poly._render
    poly._render = function (ctx) {
        const ret = poly._render_super(ctx)
        ctx.font = '24px Arial';
        ctx.fillStyle = '#000';
        ctx.textAlign = 'center';
        ctx.fillText(this._value, 0, 0);
        return ret
    }

    poly.on('mousedblclick', () => {
        poly._toggle_editing();
        canvas.requestRenderAll();
    });

    canvas.add(poly);
    if (focus) {
        canvas.setActiveObject(poly)
    }
}

function load_roi_json(file, on_success) {
    if (!file) return;

    const reader = new FileReader();

    reader.onload = (e) => {
        try {
            let pd = []
            const json = JSON.parse(e.target.result);
            json.forEach(obj => {
                pd.push({
                    type: 0,
                    value: obj.id,
                    points: obj.points.map(pt => ({
                        x: parseInt(pt[0] * 100000 / JSON_ROI_SIZE.w),
                        y: parseInt(pt[1] * 100000 / JSON_ROI_SIZE.h),
                    }))
                })
            })

            add_saved(pd)
        } catch (err) {
            alert('JSON parse error: ' + err.message)
        }
    };

    reader.onerror = () => {
        alert('An error occurred while reading the json file.')
    };

    reader.readAsText(file, 'utf-8');
}

function load_poly_data() {
    const data = [];

    canvas.getObjects('polygon').forEach(poly => {
        const matrix = poly.calcTransformMatrix();
        const points = poly.points.map(pt => {
            const point = new fabric.Point(pt.x - poly.pathOffset.x, pt.y - poly.pathOffset.y);
            return fabric.util.transformPoint(point, matrix);
        }).map(p => ({
            x: parseInt(p.x * 100000 / CANVAS_SIZE.w),
            y: parseInt(p.y * 100000 / CANVAS_SIZE.h),
        }));

        data.push({
            "id": poly._id,
            "type": poly._type,
            "value": poly._value.toString().trim(),
            "points": points
        });
    });

    return data
}

assign_modal_el.addEventListener("show.bs.modal", e => {
    const poly = canvas.getActiveObject();
    assign_modal_el.querySelector("form label").innerText = poly._label;
    assign_modal_el.querySelector(".modal-title").innerText = poly._label;
    assign_modal_el.querySelector("form input").value = poly._value;
});

assign_modal_el.addEventListener("shown.bs.modal", e => {
    assign_modal_el.querySelector("form input").focus()
});

assign_modal_el.querySelector("form").addEventListener("submit", e => {
    e.preventDefault();
    const poly = canvas.getActiveObject();
    poly._value = assign_modal_el.querySelector("form input").value;
    canvas.requestRenderAll();
    assign_modal.hide()
});

canvas.on('mouse:down', function (opt) {
    const e = opt.e;

    const active = canvas.getActiveObject();
    if (!active || active.type !== 'polygon' || !active._editing) return;

    if (e.shiftKey) {
        const p = canvas.getPointer(e);
        remove_nearest_point(active, p);
    } else if (e.altKey) {
        add_point_on_longest_edge(active)
    }
});

window.addEventListener('keydown', e => {
    const isLeft = e.code === "ArrowLeft"
    const isRight = e.code === "ArrowRight"
    if (e.code === "Space") {
        const active = canvas.getActiveObject();
        if (!active || active.type !== 'polygon') return;

        assign_id(active);
    } else if (isLeft || isRight) {
        const next = roiJsonIndex + (isLeft ? -1 : 1)
        if (next < -1) return
        if (next >= roiJsonFiles.length) return

        if (roiJsonIndex === -1) {
            savedPolygons = load_poly_data()
        }
        canvas.getObjects('polygon').forEach(p => canvas.remove(p))

        if (next === -1) {
            add_saved(savedPolygons)
            roi_json_el.innerHTML = ""
        } else {
            roi_json_el.innerHTML = roiJsonFiles[next].name
            load_roi_json(roiJsonFiles[next])
        }

        roiJsonIndex = next
        canvas.requestRenderAll();
    }
})

document.querySelectorAll("#id_buttons button").forEach(btn => {
    btn.addEventListener("click", (e) => {
        if (loading_el) {
            alert("Loading...");
            return;
        }

        poly_add(undefined, parseInt(btn.dataset.type), btn.dataset.label);
    })
});

document.querySelector("#id_btn_save").addEventListener("click", e => {
    const data = load_poly_data()

    fetch("", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...csrf_header()
        },
        body: JSON.stringify(data)
    }).then(res => res.json()).then(r => {
        const msg = [r.message]
        if (r.errors) {
            msg.push("");
            r.errors.forEach(err => {
                Object.keys(err).forEach(key => {
                    msg.push(key);
                    err[key].forEach(em => msg.push("- " + em));
                })
            })
        }

        alert(msg.join("\n"));
    }).catch(e => {
        alert("Failed to Save!");
    })
})

document.querySelector("#id_input_load_json").addEventListener("change", e => {
    roiJsonFiles = Array.from(e.target.files || []);
    if (roiJsonIndex !== -1) {
        canvas.getObjects('polygon').forEach(p => canvas.remove(p))
        add_saved(savedPolygons)
        roiJsonIndex = -1
        roi_json_el.innerHTML = ""
    }
    alert(`Loaded ${roiJsonFiles.length}`)
})

init_icons();

