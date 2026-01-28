//camera-roi.js da ham o'zgarishi kerak, agar o'zgarsa
const CANVAS_SIZE = {w: 1024, h: 576}
// const CENTER = {x: CANVAS_SIZE.w / 2, y: CANVAS_SIZE.h / 2}
const SELECTED_FILL = 'rgba(27,94,32,0.75)';
const TRANSPARENT = 'rgba(255,235,59,0.5)';
const editable = document.currentScript.dataset.edit.toLowerCase() === "true"

const save_el = document.querySelector("#id_saved")
const marked_el = document.querySelector("#id_marked")
const next_btn = document.querySelector("#id_next_btn")
const yes_btn = document.querySelector("#id_yes")
const no_btn = document.querySelector("#id_no")

const canvas_el = document.querySelector("#id-ai-stall-mark");
const canvas = new fabric.Canvas(canvas_el, {
    width: CANVAS_SIZE.w,
    height: CANVAS_SIZE.h
});
canvas.selection = false;

let marked = {}
if (marked_el) {
    const marked_data = JSON.parse(marked_el.innerText)
    if (marked_data && Array.isArray(marked_data)) {
        marked_data.forEach(md => {
            marked[md.id] = md.is_occupied
        })
    }
}

function load_saved() {
    if (!save_el) {
        return;
    }

    const save = JSON.parse(save_el.innerText);
    if (!Array.isArray(save)) {
        return
    }

    save.forEach(pd => {
        const points = pd.points.map(p => ({
            x: parseInt(CANVAS_SIZE.w * p.x / 100000),
            y: parseInt(CANVAS_SIZE.h * p.y / 100000),
        }))
        const center = {
            left: Math.min(...points.map(p => p.x)),
            top: Math.min(...points.map(p => p.y)),
        }
        if (pd.type === 0) {
            //Faqat rasta, bu camera-rio.j2 da button da ko'rsastilgan, type lar
            poly_add(pd.id, pd.type, pd.value, points, center, false);
        }
    })
}

function poly_add(id, type, value, points, center) {
    const poly = new fabric.Polygon(points, {
        left: center.left,
        top: center.top,
        fill: TRANSPARENT,
        strokeWidth: 3,
        stroke: 'grey',
        objectCaching: false,
        transparentCorners: false,
        cornerColor: 'blue',
        selectable: false,
        hasControls: false,
        hasBorders: false,
        evented: true,
        hoverCursor: 'pointer',
    });

    poly._is_occupied = (typeof marked[id] !== "undefined") ? marked[id] : false;
    poly._id = id;
    poly._type = type;
    poly._value = value;

    function update_fill() {
        poly.set('fill', poly._is_occupied ? SELECTED_FILL : TRANSPARENT);
    }

    if (editable) {
        poly.on('mousedown', function () {
            poly._is_occupied = !poly._is_occupied
            update_fill()
            canvas.requestRenderAll();
        });
    }

    update_fill()
    canvas.add(poly);
}

function save(dataset_id, data, on_success) {
    fetch("", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...csrf_header()
        },
        body: JSON.stringify({
            "id": dataset_id,
            "data": data
        })
    }).then(r => r.json()).then(r => {
        const msg = [r.message]
        if (r.errors) {
            msg.push("");
            msg.push(JSON.stringify(r.errors));
            alert(msg.join("\n"));
        }

        if (r.success && on_success) {
            on_success()
        }
    }).catch(e => alert(e))
}

if (next_btn) {
    next_btn.addEventListener("click", function () {
        const data = [];

        canvas.getObjects('polygon').forEach(poly => {
            data.push({
                "id": poly._id,
                "is_occupied": poly._is_occupied
            });
        });

        save(next_btn.dataset.id, data, () => {
            if (next_btn.dataset.href) {
                window.location.href = next_btn.dataset.href;
            } else {
                window.location.reload()
            }
        })
    })
} else if (yes_btn && no_btn) {
    function save_yesno(dataset_id, is_ok) {
        save(dataset_id, is_ok, () => {
            window.location.reload()
        })
    }

    yes_btn.addEventListener("click", () => {
        save_yesno(yes_btn.dataset.id, true)
    })

    no_btn.addEventListener("click", () => {
        save_yesno(no_btn.dataset.id, false)
    })
}

load_saved()

document.addEventListener("keyup", function (e) {
    let cls = ""
    if (e.key === "ArrowLeft" || e.key === "a") {
        cls = "key-left"
    } else if (e.key === "ArrowRight" || e.key === "d") {
        cls = "key-right"
    }

    if (cls.length > 0) {
        const btn = document.querySelector(`button.${cls}, a.${cls}`)
        if (btn) {
            const event = new MouseEvent("click", {
                bubbles: true,
                cancelable: true,
                view: window
            });

            btn.dispatchEvent(event)
        }
    }
})