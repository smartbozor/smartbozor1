document.addEventListener("DOMContentLoaded", function () {
    const mdl_el = document.querySelector("#id-ajax-modal")
    const mdl = new bootstrap.Modal(mdl_el)
    const mdl_body = mdl_el.querySelector(".modal-body")
    let pk = undefined;
    const formatterNumber = new Intl.NumberFormat('uz', {style: "currency", currency: "UZS", maximumFractionDigits: 0});

    function set_title(title) {
        mdl_el.querySelector(".modal-header span").innerText = title
    }

    function set_loading() {
        mdl_body.innerHTML = `<div class="text-center p-4"><div class="spinner-border"></div></div>`
    }

    const edit_input = `<div class="input-group flex-nowrap"><input name="a" class="form-control py-1" style="width: 150px"/><button type="button" class="btn btn-primary btn-sm px-3 py-1"><span class="bi bi-floppy"></span></button></div>`

    mdl_el.addEventListener('show.bs.modal', (e) => {
        pk = parseInt(e.relatedTarget.dataset.pk) || undefined

        set_title("Loading...")
        set_loading()

        fetch(e.relatedTarget.dataset.url, {
            method: "PATCH",
            headers: csrf_header(),
        }).then(r => r.json()).then(r => {
            set_title(r.title)
            let html = `<table class="table table-striped table-hover align-middle">`
            let colspan = 1
            if (r.headers) {
                colspan = r.headers.length

                html += `<thead><tr class="table-dark">`
                r.headers.forEach(h => {
                    html += `<td>${h}</td>`
                })

                if (r.editable) {
                    html += '<td style="width: 1%"></td>'
                }
                html += `</tr></thead>`
            }

            if (r.data) {
                html += `<tbody>`
                r.data.forEach((row, i) => {
                    html += `<tr>`
                    row.forEach(r => {
                        html += `<td>${r}</td>`
                    })
                    if (r.editable) {
                        const [row_id, amount, can_edit] = r.editable[i]
                        if (can_edit) {
                            html += `<td class="cursor-pointer" data-id="${row_id}" data-amount="${amount}"><span class="bi bi-pencil"></span></td>`
                        } else {
                            html += '<td></td>'
                        }
                    }
                    html += `</tr>`
                })
                if (r.data.length === 0) {
                    html += `<tr><td colspan="${colspan}">${gettext("Ma'lumot topilmadi")}</td>`
                }
                html += `</tbody>`
            }

            html += `</table>`
            mdl_body.innerHTML = html

            mdl_body.querySelectorAll("td[data-id]").forEach(el => {
                el._html = el.innerHTML
                el.addEventListener("click", function (e) {
                    if (el.querySelector("input")) {
                        e.preventDefault()
                        return
                    }

                    el.innerHTML = edit_input
                    const inp = el.querySelector("input")
                    const btn = el.querySelector("button")
                    inp.value = el.dataset.amount
                    btn.addEventListener("click", function (){
                        inp.disabled = true
                        btn.disabled = true
                        btn.querySelector("span").classList.remove("bi", "bi-floppy")
                        btn.querySelector("span").classList.add("spinner-border", "spinner-border-sm")
                        el.dataset.amount = inp.value

                        fetch("", {
                            method: "PUT",
                            headers: csrf_header(),
                            body: JSON.stringify({id: el.dataset.id, amount: parseInt(inp.value) || 0})
                        }).then(r => r.json()).then(r => {
                            if (r.success) {
                                el.innerHTML = el._html
                                el.closest("td").previousElementSibling.innerHTML = formatterNumber.format(inp.value)
                            } else {
                                alert(r.error)
                            }
                        }).catch(e => {
                            alert(e.toString())
                        })
                    })
                })
            })
        }).catch(e => alert(e))
    })

    mdl_el.addEventListener("hidden.bs.modal", function (e) {
        if (pk) {
            const url = new URL(window.location.href);
            url.searchParams.set("hl", pk);
            window.location.href = url.toString();
        } else {
            window.location.reload()
        }
    })
});