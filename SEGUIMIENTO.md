# Seguimiento del desarrollo

Punto de corte: **27 de agosto de 2026**, al cerrar **COM001 — Maestro de proveedores**.

## Parches transversales

### MOD000 — Regla Entrada / Derivado / Snapshot (hecho)

- Regla incorporada al skill y a la regla permanente del proyecto.
- Entrada: hechos conocidos por el usuario.
- Derivado: consecuencias calculadas por Django en `services/`.
- Snapshot: valores calculados que deben conservar historia.
- Los estados calculables se obtienen desde hechos; las decisiones de flujo se ejecutan mediante acciones.
- Siguiente parche: `MOD001` — Adecuación de Remuneraciones.

### MOD001 — Adecuación de Remuneraciones (hecho)

- Formularios revisados: entradas explícitas y exclusión de snapshots/totales derivados.
- Períodos, finiquitos y liquidaciones mantienen estados controlados por acciones y servicios.
- Movimientos manuales ya no ofrecen conceptos de naturaleza únicamente automática; movimientos calculados no se editan manualmente.
- Tests REM: 136 OK.
- Tests MOD001: formulario y conceptos automáticos protegidos.
- REM005-C01 ya estaba implementado en el código; se verificó contra la especificación y su migración `remuneraciones.0008_pago_remuneracion_anulacion` está aplicada.
- La suite cubre sobrepagos, pagos parciales/totales, anulación auditable y reversión de estado.
- Siguiente parche: `MOD002` — Adecuación de Rendiciones.

### MOD002 — Adecuación de Rendiciones (hecho)

- Formularios ordinarios mantienen únicamente trabajador, fecha, descripción, total declarado y observaciones; detalles y respaldos siguen siendo entradas reales.
- Totales, diferencia y cuadratura permanecen calculados desde la distribución en `services/`.
- Estados se mantienen como acciones controladas; la reapertura ahora solicita motivo en la UI y deja trazabilidad en observaciones.
- Tests de Rendiciones: 69 OK.
- Siguiente parche: `MOD003` — Adecuación de Facturación.

### MOD003 — Adecuación de Facturación (hecho)

- Formularios de documentos y cobros no exponen IVA, total, tasa, estado ni saldos calculados como entradas manuales.
- Los estados y saldos se recalculan mediante servicios; documentos anulados no admiten nuevos cobros.
- Los cobros de ventas ahora tienen anulación explícita con usuario, fecha y motivo, y el saldo excluye cobros anulados.
- La anulación de documentos desde la UI exige motivo y conserva trazabilidad en observaciones.
- Migración aplicada: `facturacion.0003_cobro_venta_anulacion`.
- Tests de Facturación: 22 OK.
- Siguiente parche: `MOD004` — Adecuación de Compras.

### MOD004 — Adecuación de Compras (hecho)

- Documento de compra recibe solo datos de entrada; IVA, total, tasa snapshot, saldo y estado se calculan o controlan por servicios.
- Pagos anulados quedan excluidos del total pagado y de la transición de estado.
- La anulación de documentos de compra exige motivo, registra usuario y bloquea documentos con pagos activos.
- Se agregó formulario y pantalla de anulación para documentos de compra.
- Tests de Facturación: 22 OK.
- Siguiente parche: `P01` — revisión transversal final.

### P01 — Revisión transversal final (hecho)

- Se verificó la separación Entrada/Derivado/Snapshot en RRHH, Rendiciones y Facturación.
- Estados de contrato y obra ya no son editables desde formularios; permanecen bajo acciones de flujo.
- Se revisaron anulaciones, motivos, auditoría, exclusión de anulados y bloqueos de nuevas operaciones.
- Regresión transversal: `rrhh facturacion rendiciones`, 113 tests OK.
- Ciclo de parches concluido.

### COM004-R — Fuente documental e IVA de compras (hecho)

- Se agregó `facturacion.services.iva_compras` como fuente derivada de `DocumentoCompra` para Impuestos.
- Incluye filtros por período, proveedor, centro de costo y tipo documental.
- Excluye anulados, conserva documentos no pagados y aplica signos automáticos a notas de crédito.
- Entrega resumen, detalle suficiente para IMP, agrupaciones y validación de consistencia matemática.
- No se creó tabla mensual ni entrada manual de IVA.
- Tests de Facturación: 26 OK.
- Siguiente especificación: `COM005-R`.

### COM005-R — Consultas, reportes y saldos de compras (hecho)

- Se agregó `facturacion.services.reportes_compras` para separar compras documentadas de pagos reales.
- Incluye resumen, filtros, agrupaciones por proveedor/centro/estado, saldos actuales e históricos y pagos por fecha de pago.
- Se agregó `FiltroComprasForm` y la vista `/facturacion/compras/resumen/` con filtros GET.
- Se preparó `filas_exportacion_compras()` sin escribir Excel ni duplicar datos.
- Los anulados y pagos anulados no contaminan los totales oficiales.
- Tests de Facturación: 26 OK.
- Siguiente especificación: `COM006-R`.

### COM006-R — Integración de Compras (hecho)

- Se agregó `facturacion.services.integracion_compras` con salidas separadas para Impuestos, Finanzas y Excel.
- Impuestos recibe documentos de compra y sus snapshots, sin pagos ni reglas de crédito fiscal.
- Finanzas recibe únicamente pagos vigentes, individualmente, con fecha de pago, centro, proveedor y clave idempotente de origen.
- Excel recibe estructuras derivadas de documentos y pagos; no recalcula ni se convierte en fuente oficial.
- El bloque Compras queda cerrado: `COM001` a `COM006-R`.
- Tests de Facturación: 29 OK.
- Siguiente bloque: `IMP001`.

### IMP001 — Períodos tributarios (hecho)

- Se implementó `PeriodoImpuesto` como unidad mensual con fechas derivadas desde año y mes.
- Se agregó el estado `VALIDADO` y servicios de flujo para validar, cerrar y reabrir períodos.
- Se agregaron vistas, rutas y formularios para listar, crear y consultar períodos.
- Los cálculos de IVA, PPM, determinación y pagos quedan reservados a `IMP002`–`IMP005`.
- Migración aplicada: `impuestos.0002_periodo_validado`.
- Tests de Impuestos: 5 OK.
- Siguiente especificación: `IMP002`.

### IMP002 — Determinación automática de IVA (hecho)

- Se implementó `impuestos.iva` para calcular IVA ventas, IVA compras, neto ventas y diferencia preliminar por período.
- Las fuentes oficiales son `DocumentoTributario` y `DocumentoCompra`; los pagos no modifican los montos documentales.
- Se excluyen anulados, se respetan snapshots históricos y se aplica signo automático a notas de crédito/débito.
- Se registran detalles de documentos utilizados y se detectan inconsistencias sin corregirlas silenciosamente.
- El recálculo solo opera sobre períodos abiertos.
- Tests de Impuestos: 8 OK.
- Siguiente especificación: `IMP003`.

### IMP003 — Determinación automática de PPM (hecho)

- Se implementó `impuestos.ppm` con base única en `neto_ventas` determinado por IMP002.
- La tasa se obtiene desde `TASA_PPM` mediante parámetros históricos y se guarda como snapshot en el período.
- El monto se calcula con `Decimal` y redondeo monetario centralizado en el servicio.
- Se detecta explícitamente la ausencia de tasa y se bloquea el recálculo de períodos cerrados.
- Tests de Impuestos: 12 OK.
- Siguiente especificación: `IMP004`.

### IMP004 — Determinación mensual, validación y cierre (hecho)

- Se implementó `impuestos.determinacion` para consolidar IVA de IMP002 y PPM de IMP003.
- La fórmula oficial es `IVA ventas - IVA compras + PPM`, conservando diferencias negativas sin convertirlas silenciosamente a cero.
- Se impide determinar o validar cuando faltan componentes oficiales.
- Se reutiliza el flujo `VALIDADO` de `PeriodoImpuesto`; los pagos reales quedan reservados para IMP005.
- Tests de Impuestos: 15 OK.
- Siguiente especificación: `IMP005`.

### IMP005 — Pagos reales de impuestos (hecho)

- Se implementó `impuestos.pagos` para registrar pagos reales y parciales desde el monto determinado por IMP004.
- El saldo y la situación de pago son derivados; los pagos posteriores al cierre están permitidos.
- Se bloquean montos no positivos y sobrepagos normales.
- Se agregó anulación auditable con usuario, fecha y motivo, excluyendo pagos anulados del saldo.
- Migración aplicada: `impuestos.0003_pago_impuesto_auditoria`.
- Tests de Impuestos: 18 OK.
- Siguiente especificación: `IMP006`.

### IMP006 — Reportes e integración tributaria (hecho)

- Se implementó `impuestos.reportes` para resúmenes mensuales, anuales, saldos y pagos por período o fecha real.
- Se distinguen obligaciones tributarias por período de egresos financieros por fecha de pago.
- Se preparó salida estructurada para Excel sin crear totales paralelos ni recalcular en la interfaz.
- No se inventan períodos inexistentes y los pagos anulados quedan excluidos.
- Tests de Impuestos: 21 OK.
- Módulo IMP cerrado: `IMP001` a `IMP006`.

Al retomar: leer `CONTEXTO.md` → este archivo → skill `.cursor/skills/nomina-sistema/SKILL.md` → mini-spec del siguiente bloque. **No rehacer** REM001–REM010 ni REN001–REN007.

## Dónde estamos

### Bloque 1 — Remuneraciones (cerrado)

| Ítem | Estado |
|------|--------|
| Infra Django | Hecho |
| REM001–REM010 | Hecho — **Bloque 1 cerrado** |

### Bloque 2 — Rendiciones (cerrado)

| Ítem | Estado |
|------|--------|
| REN001 Registro de rendición | Hecho |
| REN002 Distribución por centro de costo | Hecho |
| REN003 Validación y cuadratura | Hecho |
| REN004 Documentos y respaldos | Hecho |
| REN005 Flujo de aprobación | Hecho |
| REN006 Consultas, filtros y reportes | Hecho |
| REN007 Preparación Finanzas e integración Excel | **Hecho — Bloque 2 cerrado** |

Orden Bloque 2: `REN001 → 002 → 003 → 004 → 005 → 006 → 007`

### Bloque 3 — Facturación

| Ítem | Estado |
|------|--------|
| FAC001 Maestro de clientes | Hecho |
| FAC002 Obras y centros de costo | Hecho |
| FAC003 Documentos tributarios de venta | Hecho |
| FAC004 Motor de cálculo tributario | Hecho |
| FAC005 Cobros y estado de pago | Hecho |
| FAC006 Consultas y reportes | Hecho |
| FAC007 Integración con Impuestos, Finanzas y Excel | Hecho |

### Bloque 4 — Compras y proveedores

| Ítem | Estado |
|------|--------|
| COM001 Maestro de proveedores | Hecho |
| COM002 Documentos de compra | Hecho |
| COM003 Pagos a proveedores | Hecho |
| COM004 IVA de compras | Pendiente |
| COM005 Consultas y reportes de compras | Pendiente |
| COM006 Integración con Impuestos, Finanzas y Excel | Pendiente |

#### COM001 — Maestro de proveedores (hecho)

- CRUD en `/facturacion/proveedores/` con listar, crear, consultar, editar y desactivar.
- RUT chileno validado y normalizado; razón social con espacios normalizados.
- Soft-delete mediante `activo=False`; el proveedor histórico no se elimina.
- Permisos Django `view_proveedor`, `add_proveedor`, `change_proveedor` y `delete_proveedor`.
- Tests agregados en `facturacion/tests.py`.

#### COM002 — Documentos de compra (hecho)

- CRUD en `/facturacion/compras/` y listado por proveedor.
- IVA y total calculados en servidor mediante `TASA_IVA`; documentos exentos quedan con IVA cero.
- Validación de proveedor, número único por proveedor/tipo, fechas y neto no negativo.
- Adjuntos PDF/JPG/JPEG/PNG de hasta 10 MB.
- Anulación controlada; el estado de pago queda reservado para COM003.
- Tests: `facturacion/tests.py` — 21 casos en total.

#### COM003 — Pagos a proveedores (hecho)

- Registro de pagos desde la ficha del documento en `/facturacion/compras/<id>/pagos/nuevo/`.
- Estados derivados `REGISTRADO`, `PARCIAL` y `PAGADO`; anulados no se contabilizan.
- Control transaccional de sobrepagos y bloqueo para documentos anulados.
- Anulación auditable con usuario, fecha y motivo; migración `facturacion.0002_pago_compra_anulacion`.
- Tests: `facturacion/tests.py` — 22 casos en total.

#### FAC001 — Maestro de clientes (hecho)

- CRUD en `/facturacion/clientes/` con listar, crear, consultar, editar y desactivar.
- RUT chileno validado y normalizado; razón social con espacios normalizados.
- Soft-delete mediante `activo=False`; no se elimina el registro histórico.
- Permisos Django `view_cliente`, `add_cliente`, `change_cliente` y `delete_cliente`.
- Tests: `facturacion/tests.py` — 4 casos.

#### FAC002 — Obras y centros de costo (hecho)

- CRUD de obras en `/facturacion/obras/` y listado filtrado por cliente.
- Cliente activo obligatorio en altas; centro de costo opcional.
- Código único, nombres normalizados y fechas validadas.
- Se conservan obras terminadas para el histórico de documentos.

#### FAC003 — Registro de documentos tributarios de venta (hecho)

- CRUD en `/facturacion/documentos/`, con listados filtrables por cliente y obra.
- IVA y total calculados en servidor usando el parámetro vigente `IVA`; documentos exentos quedan con IVA cero.
- Valida pertenencia cliente/obra, número único, fechas y neto no negativo.
- Anulación mediante acción específica, conservando el documento histórico.
- Tests: `facturacion/tests.py` — 10 casos en total.

#### FAC004 — Motor de cálculo tributario (hecho)

- Servicio centralizado en `facturacion/services/documentos.py`.
- Usa el parámetro vigente `TASA_IVA` y guarda la tasa utilizada en `tasa_iva_snapshot`.
- Redondea IVA monetario a centavos con `ROUND_HALF_UP`; exentos quedan con IVA cero.
- Impide recalcular documentos no emitidos o con cobros.

#### FAC005 — Cobros y estado de pago (hecho)

- Registro y edición de cobros desde la ficha del documento.
- Control de sobrepago y bloqueo para documentos anulados.
- Estado derivado automáticamente: `EMITIDA`, `PARCIAL` o `PAGADA`.
- Ficha muestra total facturado, cobrado, saldo y detalle de cobros.

#### FAC007 — Integración con Impuestos, Finanzas y Excel (hecho)

- Interfaces en `facturacion/services/integracion.py`, sin implementar todavía los módulos destino.
- Salida tributaria por fecha de emisión; salida financiera por fecha efectiva de cobro.
- Filas Excel normalizadas con `ITEM` de presentación y exclusión de documentos anulados.
- Tests: `facturacion/tests.py` — 15 casos en total.

#### FAC006 — Consultas y reportes de facturación (hecho)

- Filtros por año, mes, fechas, cliente, obra, tipo, estado y centro de costo.
- Resumen Django de neto, IVA, total facturado, cobrado, saldo y anulados.
- Interfaz `/facturacion/resumen/` y servicio `facturacion/services/reportes.py`.
- Los anulados se muestran, pero no suman en los totales oficiales.
- Tests: `facturacion/tests.py` — 16 casos en total.

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

### REN006 — Consultas, filtros y reportes (hecho)

- `services/reportes.py`: `filtrar_rendiciones`, `resumen_por_centro`, `filas_exportacion`
- Listado: filtros año/mes/trabajador/CC/estado/fecha (`FiltroRendicionForm`)
- Resumen: `/rendiciones/resumen/` — totales por centro y trabajador; default APROBADA+PAGADA
- Tests: `rendiciones/test_reportes.py` — **9 OK** (suite rendiciones **61 OK**)

### REN007 — Preparación Finanzas e integración Excel (hecho — cierra Bloque 2)

- `services/integracion.py`: `datos_financieros()`, `filas_excel()`, `estado_financiero()`, claves idempotentes `REN-{id}-DET-{detalle}`
- Solo **APROBADA** elegible para Finanzas; un ítem EGRESO por línea de CC
- Matriz Excel dinámica (columnas CC según datos; BODEGA no rompe el modelo)
- Ficha: indicador «Estado financiero» (pendiente / registrada / pagada)
- **Sin** crear MovimientoFinanciero ni export Excel (queda para bloques posteriores)
- Tests: `rendiciones/test_integracion.py` — **8 OK** (suite rendiciones **69 OK**)

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
- Primera tarea: **siguiente bloque del sistema** (Facturación / compras, según roadmap)
  1. Leer mini-specs del bloque 3 cuando existan en `otros/mini-especificaciones/`
  2. No reabrir REN ni REM cerrados
  3. Finanzas consumirá `datos_financieros()`; Excel usará `filas_excel()` / `filas_exportacion()`


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
