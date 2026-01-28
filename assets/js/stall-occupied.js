document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll("[data-occupied]").forEach(it => {
        it.addEventListener("click", e => {
            fetch("", {
                method: "PUT",
                headers: {
                    'Content-Type': 'text/plain; charset=utf-8',
                    ...csrf_header()
                },
                body: it.dataset.occupied.toString()
            }).then(r => r.json()).then(r => {
                if (r.success) {
                    it.closest("tr").querySelectorAll(".badge-occupied").forEach(el => {
                        el.classList.toggle("bg-success", r.is_occupied)
                        el.classList.toggle("bg-danger", !r.is_occupied)
                        el.innerText = r.title
                    })
                } else {
                    alert(r.message)
                }
            }).catch(e => {
                alert(e)
            })
        })
    })
});