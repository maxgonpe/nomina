(function () {
  function initChart() {
    var dataEl = document.getElementById("resumen-grafico-data");
    var canvas = document.getElementById("grafico-resumen-anual");
    if (!dataEl || !canvas || typeof Chart === "undefined") {
      return;
    }
    var data = JSON.parse(dataEl.textContent);
    new Chart(canvas, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Total mensual",
            data: data.valores,
            backgroundColor: "rgba(33, 37, 41, 0.75)",
            borderColor: "rgba(33, 37, 41, 1)",
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                var n = ctx.parsed.y || 0;
                return n.toLocaleString("es-CL", {
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0,
                });
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function (value) {
                return Number(value).toLocaleString("es-CL");
              },
            },
          },
        },
      },
    });
  }

  function initYearNav() {
    var select = document.querySelector("[data-resumen-anio]");
    var form = document.getElementById("form-resumen-anual");
    if (!select || !form) {
      return;
    }
    select.addEventListener("change", function () {
      var anio = select.value;
      var params = new URLSearchParams(new FormData(form));
      params.delete("anio_nav");
      var qs = params.toString();
      window.location.href =
        "/remuneraciones/resumen/" + anio + "/" + (qs ? "?" + qs : "");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initChart();
    initYearNav();
  });
})();
