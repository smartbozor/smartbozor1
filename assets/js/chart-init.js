document.addEventListener("DOMContentLoaded", function () {
    window.init_chart.forEach(([key, data]) => {
        new Chart(document.querySelector("#" + key), {
            type: data.type,
            data: data.data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                ...(data.options || {}),
            }
        })
    });
});