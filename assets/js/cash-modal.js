document.addEventListener("DOMContentLoaded", function () {
    const mdl_el = document.querySelector("#id-cash-modal")
    const mdl = new bootstrap.Modal(mdl_el)
    let close_timer = null;
    let pk = undefined;
    let post_url = "";

    mdl_el.addEventListener("show.bs.modal", function (e) {
        e.target.querySelector("form").reset()
        Object.keys(e.relatedTarget.dataset).forEach(key => {
            const is_readonly = key.endsWith("_readonly")
            const is_hidden = key.endsWith("_hide")
            const value = e.relatedTarget.dataset[key]
            if (is_readonly) key = key.substring(0, key.length - 9)
            if (is_hidden) key = key.substring(0, key.length - 5)

            const el = e.target.querySelector(`.${key}`)
            if (!el) {
                return
            }

            if (is_hidden) {
                const parent_el = el.closest(".parent-el");
                if (parent_el) {
                    parent_el.classList.add("d-none");
                    return;
                }
            }

            if ('value' in el) {
                el.value = value
                if (is_readonly) {
                    el.setAttribute("readonly", "readonly")
                }
            } else {
                el.innerText = value
            }
        });

        pk = e.relatedTarget.dataset.pk;
        post_url = e.relatedTarget.dataset.url || "";
    });

    mdl_el.addEventListener("hidden.bs.modal", function (e) {
        if (close_timer) {
            clearInterval(close_timer);
            close_timer = null;
        }

        if (pk) {
            const url = new URL(window.location.href);
            url.searchParams.set("hl", pk);
            url.searchParams.delete("amount")
            window.location.href = url.toString();
        } else {
            window.location.reload()
        }
    })

    document.querySelector("#id-cash-form").addEventListener("submit", function (e) {
        e.preventDefault();

        const data = new FormData(e.target);
        Array.from(e.target.elements).forEach(el => {
            el.disabled = true
            if (el.classList.contains("is-invalid")) {
                el.classList.remove("is-invalid");
                el.parentElement.querySelector(".invalid-feedback").remove()
            }
        });

        fetch(post_url, {
            method: "POST",
            headers: csrf_header(),
            body: data
        }).then(r => r.json()).then(r => {
            if (r.success) {
                const alert = document.createElement("div")
                alert.classList.add("alert")
                alert.classList.add("alert-success")
                alert.innerText = r.message;
                e.target.parentElement.appendChild(alert)

                const timer = document.createElement("div")
                timer.classList.add("mt-3")
                timer.classList.add("text-center")
                timer.classList.add("f-5")
                timer.innerText = "5"
                e.target.parentElement.appendChild(timer)

                let n = 4
                close_timer = setInterval(function () {
                    timer.innerText = n.toString()
                    n -= 1;
                    if (n <= 0) {
                        clearInterval(close_timer)
                        mdl.hide()
                    }
                }, 1000)
                e.target.remove()
                return;
            }

            Array.from(e.target.elements).forEach(el => el.disabled = false);

            if (typeof r.error === "string") {
                alert(r.error);
            } else {
                Object.keys(r.error).forEach(key => {
                    const inp = e.target.querySelector(`input[name="${key}"]`)
                    inp.classList.add("is-invalid");

                    const feedback = document.createElement("div");
                    feedback.classList.add("invalid-feedback");
                    feedback.innerText = r.error[key][0];

                    inp.parentElement.appendChild(feedback);
                })
            }
        }).catch(e => alert(e));
    });
});