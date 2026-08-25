# Seguimiento del desarrollo

Punto de corte: **25 de agosto de 2026**, al cerrar **REN005** (flujo de aprobación).

Al retomar: leer `CONTEXTO.md` → este archivo → skill `.cursor/skills/nomina-sistema/SKILL.md` → mini-spec REN en `otros/mini-especificaciones/REN/` (o PDF en `otros/pdf/`). **No rehacer** REM001–REM010 ni REN001–REN005.

## Dónde estamos

### Bloque 1 — Remuneraciones (cerrado)

| Ítem | Estado |
|------|--------|
| Infra Django | Hecho |
| REM001–REM010 | Hecho — **Bloque 1 cerrado** |

Orden ejecutado: `001 → 002 → 003 → 004 → 006 → 007 → 008 → 005 → 009 → 010`

### Bloque 2 — Rendiciones (en curso)

| Ítem | Estado |
|------|--------|
| REN001 Registro de rendición | Hecho |
| REN002 Distribución por centro de costo | Hecho |
| REN003 Validación y cuadratura | Hecho |
| REN004 Documentos y respaldos | Hecho |
| REN005 Flujo de aprobación | **Hecho** |
| REN006 Consultas, filtros y reportes | **Siguiente** |
| REN007 Preparación Finanzas e integración Excel | Pendiente |

Orden del Bloque 2:

`REN001 → 002 → 003 → 004 → 005 → 006 → 007`

Specs: `otros/mini-especificaciones/REN/*.docx` (fuente completa). PDF en `otros/pdf/REN00X…` (algunos exportan casi vacíos; si falta texto, usar el docx). Visión del bloque: `otros/mini-especificaciones/REN/bloque2 — rendiciones.docx` y `Dependencias del Bloque 2.docx`. Referencia corta: `.cursor/skills/nomina-sistema/referencia-bloque2-rendiciones.md`.

Excel origen de rendiciones: `otros/PLANILLA DE PAGOS GENERALES 2026.xlsx` (distribución por CASA/EGC/CGA/OFI sin columnas fijas en BD).

Modelos en `rendiciones/`: `Rendicion`, `RendicionDetalle`, `DocumentoRendicion` (+ admin).

### REN001 — Registro de rendición (hecho)

- UI: `/rendiciones/` listar · `/nueva/` · `/<pk>/` · `/<pk>/editar/` · `/<pk>/anular/`
- `RendicionForm` + CBV con mixins del Bloque 1; estado inicial forzado a `BORRADOR`
- Alta solo con trabajador activo; edición solo en borrador; anular borrador → `ANULADA` (sin borrar)
- Filtros listado: trabajador, estado; ficha muestra totales de cuadratura (aún sin detalles)
- Servicio: `rendiciones/services/rendiciones.py` (`anular`, `puede_editar`)
- Tests: `rendiciones/tests.py` — **12 OK**

### REN002 — Distribución por centro de costo (hecho)

- UI: ficha muestra tabla de líneas; edición en `/rendiciones/<pk>/distribucion/`
- `RendicionDetalleForm` + `RendicionDetalleFormSet` (inline; varias líneas al mismo CC OK)
- Servicio: `guardar_distribucion()`, `agregar_detalle()`, `total_distribuido` / `diferencia`
- Solo editable en BORRADOR; CC activo en altas; histórico conserva CC inactivo
- JS preliminar: `static/rendiciones/js/distribucion.js` (suma/diferencia; servidor manda)
- Tests: `rendiciones/test_distribucion.py` — **10 OK** (suite rendiciones **22 OK**)

### REN003 — Validación y cuadratura (hecho)

- `validar_cuadratura()`: exige detalles, `total_declarado > 0`, `diferencia == Decimal("0.00")`
- `presentar()`: solo BORRADOR → PRESENTADA si cuadra; POST en `/rendiciones/<pk>/presentar/`
- GET de confirmación muestra totales; no cambia estado
- Ficha: errores de cuadratura + botón Presentar si cuadra
- Tests: `rendiciones/test_cuadratura.py` — **11 OK** (suite rendiciones **33 OK**)

### REN004 — Documentos y respaldos (hecho)

- `DocumentoRendicionForm`: PDF/JPG/PNG, máx. 10 MB; `upload_to` → `media/rendiciones/<año>/<id>/`
- UI: sección en ficha; `/rendiciones/<pk>/documentos/agregar/` · `/documentos/<pk>/eliminar/`
- Alta/baja solo en BORRADOR (`puede_editar_documentos`); migración `0002_documento_upload_to`
- Tests: `rendiciones/test_documentos.py` — **7 OK** (suite rendiciones **40 OK**)

### REN005 — Flujo de aprobación (hecho)

- `services/estados.py`: presentar / aprobar / rechazar / reabrir / anular + `acciones_disponibles`
- Transiciones: BORRADOR→PRESENTADA→APROBADA|RECHAZADA→(reabrir)BORRADOR; anular desde borrador/presentada/rechazada
- Campo `motivo_rechazo`; motivo obligatorio en rechazo y anulación
- Permisos: `presentar_rendicion`, `aprobar_rendicion`, `rechazar_rendicion`, `anular_rendicion`
- URLs: `/presentar/` `/aprobar/` `/rechazar/` `/reabrir/` `/anular/` (cambio de estado solo POST)
- Migración `0003_flujo_aprobacion`
- Tests: `rendiciones/test_estados.py` — **11 OK** (suite rendiciones **52 OK**)

## Qué quedó construido (Bloque 1 — no rehacer)

### Infra

- Proyecto Django 5.2, SQLite, venv en `.env/`
- Apps: `core`, `rrhh`, `remuneraciones`, `rendiciones`, `facturacion`, `impuestos`, `finanzas`, `contabilidad`, `integracion_excel`
- Locale `es-cl`, zona `America/Santiago`, fechas `dd-mm-yyyy`
- Migraciones: `rrhh` 0002, `core` 0002, `remuneraciones` 0007
- Tests Bloque 1: **120 OK** (`python manage.py test rrhh core remuneraciones`)

### REM001–REM010 (resumen)

- Trabajadores, cargos/contratos/anexos, períodos, conceptos/parámetros
- HE, movimientos, finiquitos, motor de liquidación, costos, resumen anual + Chart.js
- Detalle histórico: ver commits y secciones anteriores del repo; bitácora viva ahora apunta al Bloque 2

## Plan de construcción — Bloque 2

### Invariantes

- Django maestro; Excel plantilla.
- **No** columnas `casa`/`egc`/`cga`/`ofi` en modelos: filas `RendicionDetalle` → `CentroCosto`.
- `Decimal` en servicios; UI Bootstrap + mixins del Bloque 1.
- No tocar REM001–REM010.
- No implementar Finanzas, IVA, asientos, facturas ni flujo de caja dentro de REN001–007 (REN007 solo prepara interfaces).

### Por ítem

| ID | App / capa | Qué hacer |
|----|------------|-----------|
| REN001 | `rendiciones` forms/views/urls | Cabecera: listar, crear, editar, detalle; BORRADOR; solo trabajador activo en alta |
| REN002 | services + formset | Detalles por CC; varias líneas al mismo CC; totales en ficha |
| REN003 | `services/rendiciones.py` | `validar_cuadratura()`; gate a PRESENTADA |
| REN004 | media + DocumentoRendicion | Upload PDF/JPG/PNG; path tipo `media/rendiciones/<año>/<id>/` |
| REN005 | `services/estados.py` | Transiciones + permisos presentar/aprobar/rechazar/anular/reabrir |
| REN006 | `services/reportes.py` | Filtros + resumen por CC + `filas_exportacion()` |
| REN007 | `services/integracion.py` | `datos_financieros()` idempotente; `filas_excel()` matriz dinámica |

### Estructura objetivo

```
rendiciones/
├── forms.py, views.py, urls.py
├── services/{rendiciones,estados,reportes,integracion}.py
├── templates/rendiciones/
├── static/rendiciones/js/
└── tests/ (o test_*.py en la app)
```

Registrar `path("rendiciones/", include("rendiciones.urls"))` en `nomina/urls.py` y nav en `templates/base.html`.

## Cómo retomar

```bash
cd /home/maxgonpe/nomina
source .env/bin/activate
python manage.py runserver 127.0.0.1:8000
```

- Login: [http://127.0.0.1:8000/cuentas/login/](http://127.0.0.1:8000/cuentas/login/)
- Primera tarea: **REN006 — Consultas, filtros y reportes**
  1. Leer `otros/mini-especificaciones/REN/REN006 — Consultas, filtros y reportes.docx`
  2. `services/reportes.py`; resumen por CC; `filas_exportacion()`
  3. Tests; actualizar esta tabla y el skill

## Roadmap de bloques (sistema completo)

```
1 Remuneraciones ✓
2 Rendiciones    ← ahora
3 Facturación + compras
4 Impuestos
5 Finanzas
6 Contabilidad
7 Integración Excel (cuando haya datos de varios módulos)
```

## Qué no hacer al retomar

- No rehacer Bloque 1 ni copiar de nuevo `otros/modelos/`.
- No crear modelos por mes/año ni columnas fijas por centro de costo.
- No meter Finanzas dentro de Rendiciones.
- No saltar REN005 sin cuadratura (REN003).
- No commitear `otros/` ni `.xlsx` salvo que el usuario lo pida.
