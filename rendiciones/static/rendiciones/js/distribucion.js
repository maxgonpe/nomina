(function () {
  const form = document.getElementById("form-distribucion");
  if (!form) return;

  const tbody = document.getElementById("filas-detalle");
  const plantilla = document.getElementById("plantilla-fila");
  const totalForms = form.querySelector('[name$="-TOTAL_FORMS"]');
  const prefix = (totalForms && totalForms.name.replace("-TOTAL_FORMS", "")) || "det";
  const totalDeclaradoEl = document.getElementById("total-declarado");
  const sumaEl = document.getElementById("suma-preliminar");
  const diffEl = document.getElementById("diff-preliminar");
  const btnAgregar = document.getElementById("btn-agregar-fila");

  function parseMonto(valor) {
    if (valor == null || valor === "") return 0;
    const cleaned = String(valor).trim().replace(/\s/g, "").replace(",", ".");
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : 0;
  }

  function totalDeclarado() {
    if (!totalDeclaradoEl) return 0;
    return parseMonto(totalDeclaradoEl.getAttribute("data-valor"));
  }

  function filasVisibles() {
    return Array.from(tbody.querySelectorAll("tr.fila-detalle")).filter((tr) => {
      const del = tr.querySelector('input[name$="-DELETE"]');
      return !(del && del.value === "on");
    });
  }

  function actualizarTotales() {
    let suma = 0;
    filasVisibles().forEach((tr) => {
      const input = tr.querySelector(".monto-detalle");
      if (input && !input.disabled) suma += parseMonto(input.value);
    });
    const diff = totalDeclarado() - suma;
    if (sumaEl) sumaEl.textContent = suma.toLocaleString("es-CL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (diffEl) {
      diffEl.textContent = diff.toLocaleString("es-CL", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      diffEl.classList.toggle("text-success", Math.abs(diff) < 0.005);
      diffEl.classList.toggle("text-danger", Math.abs(diff) >= 0.005);
    }
  }

  function marcarEliminada(tr) {
    const del = tr.querySelector('input[name$="-DELETE"]');
    const idField = tr.querySelector('input[name$="-id"]');
    if (idField && idField.value) {
      if (del) del.value = "on";
      tr.style.display = "none";
    } else {
      tr.remove();
      renumerar();
    }
    actualizarTotales();
  }

  function renumerar() {
    const filas = Array.from(tbody.querySelectorAll("tr.fila-detalle"));
    filas.forEach((tr, i) => {
      tr.querySelectorAll("input, select, textarea").forEach((el) => {
        if (!el.name) return;
        el.name = el.name.replace(new RegExp("^" + prefix + "-\\d+-"), prefix + "-" + i + "-");
        if (el.id) {
          el.id = el.id.replace(new RegExp("^id_" + prefix + "-\\d+-"), "id_" + prefix + "-" + i + "-");
        }
      });
    });
    if (totalForms) totalForms.value = String(filas.length);
  }

  function agregarFila() {
    if (!plantilla || !totalForms) return;
    const html = plantilla.innerHTML.replace(/__prefix__/g, totalForms.value);
    const wrap = document.createElement("tbody");
    wrap.innerHTML = html.trim();
    const tr = wrap.firstElementChild;
    tbody.appendChild(tr);
    totalForms.value = String(Number(totalForms.value) + 1);
    actualizarTotales();
  }

  tbody.addEventListener("click", (ev) => {
    const btn = ev.target.closest(".btn-quitar");
    if (!btn) return;
    marcarEliminada(btn.closest("tr.fila-detalle"));
  });

  tbody.addEventListener("input", (ev) => {
    if (ev.target.classList.contains("monto-detalle")) actualizarTotales();
  });

  if (btnAgregar) btnAgregar.addEventListener("click", agregarFila);

  actualizarTotales();
})();
