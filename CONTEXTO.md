# CONTEXTO — Sistema de nómina (Sistemas Hídricos)

Documento de handoff. Sirve de **prompt** para un chat nuevo cuando se agoten los tokens. El estado vivo del código está en [`SEGUIMIENTO.md`](SEGUIMIENTO.md); este archivo explica *por qué* se construye así y *cómo* continuar.

---

## Prompt para pegar en un chat nuevo

```
Continúa el sistema Django de nómina en /home/maxgonpe/nomina.

Lee en este orden, sin rehacer lo ya cerrado:
1. CONTEXTO.md (este archivo)
2. SEGUIMIENTO.md (punto exacto del desarrollo)
3. .cursor/skills/nomina-sistema/SKILL.md
4. .cursor/skills/nomina-sistema/referencia-bloque2-rendiciones.md
5. La mini-especificación del siguiente ítem en otros/mini-especificaciones/REN/
   (docx; PDF en otros/pdf/ son respaldo — algunos exportan casi vacíos)

Siguiente tarea: Bloque 3 — Facturación + compras (cuando haya mini-specs).
Bloque 1 (REM) y Bloque 2 (REN001–REN007) cerrados — no rehacerlos.
Django es la fuente oficial. Finanzas/Excel consumirán las APIs internas de REN007.
UI en español (Chile).
Orden bloques: 1 Remuneraciones ✓ → 2 Rendiciones ✓ → 3 Facturación → 4 Impuestos → 5 Finanzas → 6 Contabilidad → 7 Integración Excel.
```

---

## Qué es el proyecto

Reemplazar dos libros Excel como fuente de verdad por un sistema Django para **Sistemas Hídricos**. Excel queda como importación/exportación, nunca como maestro.

**Excel origen** (en `otros/`, gitignored):

| Libro | Contenido |
|-------|-----------|
| `NOMINA REMUNERACIONES 2026.xlsx` | Una hoja por mes (ene–dic) + RESUMEN 2026. Cada mes: 3 tablas (liquidación, horas extra, costo trabajador). Columnas variables entre meses. Identidad hoy: nombre + C.I. |
| `PLANILLA DE PAGOS GENERALES 2026.xlsx` | Gastos, **rendiciones por centro** (CASA/EGC/CGA/OFI), facturación, impuestos, balance. Los sueldos se alimentan desde la nómina. |

Sep–dic 2026 en el Excel son **plantilla**. Tener la hoja no significa que el período esté abierto.

**Especificaciones:**

| Bloque | Dónde |
|--------|-------|
| Remuneraciones (cerrado) | `otros/mini-especificaciones/` REM* + `otros/pdf/` |
| **Rendiciones (activo)** | `otros/mini-especificaciones/REN/` (docx) + `otros/pdf/REN*` |
| Análisis global | `otros/pdf/analisis-del-sistema.pdf` |
| Modelos de referencia | `otros/modelos/` (ya copiados a las apps) |

---

## Conclusiones del análisis

1. **No modelar el Excel.** No hay `NominaAgosto` ni columnas fijas por bono. Un mes es un `PeriodoRemuneracion`. Un haber/descuento nuevo es un `ConceptoRemuneracion` + `MovimientoRemuneracion`.
2. **Identidad por RUT**, no por nombre. Validar DV; guardar `rut_normalizado` único.
3. **Parámetros con vigencia.** `FACTOR_HE`, IVA, PPM, etc.: `ParametroNegocio` + `ParametroValor`. Nunca hardcodear. Consultar `valor("FACTOR_HE", fecha)`.
4. **Snapshots en liquidación.** Sueldo, cargo y CC se congelan al calcular.
5. **Centros de costo por alias.** OFC/OFI/OFICINA CENTRAL = mismo centro. Homologar con `AliasCentroCosto`. En rendiciones: filas `RendicionDetalle` → FK a `CentroCosto`, **nunca** columnas CASA/EGC/CGA/OFI.
6. **Cálculo en `services/`**, no en views ni en Excel. Dinero: `Decimal`.
7. **Soft-delete / anulación:** no borrar históricos.
8. **Bloque 2:** cuadratura `total_declarado == total_distribuido` es gate a PRESENTADA; Finanzas solo consume interfaces (REN007), no se implementa dentro de REN.

Fórmulas Bloque 1: `.cursor/skills/nomina-sistema/referencia-dominio.md`.  
Plan Bloque 2: `.cursor/skills/nomina-sistema/referencia-bloque2-rendiciones.md`.

---

## Decisiones y diseño a seguir

### Apps (no fusionar, no renombrar)

`core` · `rrhh` · `remuneraciones` · `rendiciones` · `facturacion` · `impuestos` · `finanzas` · `contabilidad` · `integracion_excel`

Modelos de todas las apps **ya existen**. Bloque 1 tiene UI/servicios. Bloque 2: modelos + admin en `rendiciones/`; falta forms/views/services.

### Orden de bloques del sistema

```
1 Remuneraciones ✓
2 Rendiciones    ← ahora (REN001–007)
3 Facturación + compras
4 Impuestos
5 Finanzas
6 Contabilidad
7 Integración Excel (cuando haya datos de varios módulos)
```

### Orden Bloque 1 (cerrado)

`REM001 → 002 → 003 → 004 → 006 → 007 → 008 → 005 → 009 → 010`

### Orden Bloque 2 (activo)

`REN001 → 002 → 003 → 004 → 005 → 006 → 007`

### Capa de implementación (mismo patrón)

1. Leer la mini-spec (REN: preferir docx en `otros/mini-especificaciones/REN/`).
2. Reutilizar el modelo; cambiarlo solo si la spec lo exige.
3. Reglas en `services/`. UI: `forms.py` + CBV (`LoginRequiredMixin` + `PermissionRequiredMixin` + `AuditFormMixin`).
4. Templates Bootstrap 5, español Chile, fechas `dd-mm-yyyy`.
5. Tests del criterio de aceptación.
6. Al cerrar el ítem: actualizar `SEGUIMIENTO.md` y el Estado del skill.

### Invariantes (no negociar)

- Django maestro; Excel plantilla.
- Período + fecha; nunca un modelo por mes/año.
- Conceptos variables no son columnas de `LiquidacionMensual`.
- Rendiciones: distribución por `RendicionDetalle`, no columnas fijas por CC.
- Relacionar por FK / RUT normalizado, nunca por nombre.
- No commitear `otros/` ni `.xlsx`.
- No meter Finanzas/IVA/asientos dentro del Bloque 2.

### Stack

Django 5.2.17, SQLite ahora (diseñar para PostgreSQL), venv en `.env/`, locale `es-cl`, zona `America/Santiago`, Bootstrap 5, Chart.js (REM010), openpyxl más adelante.

### Cómo levantar

```bash
cd /home/maxgonpe/nomina
source .env/bin/activate
python manage.py runserver 127.0.0.1:8000
python manage.py test rrhh core remuneraciones   # 120 OK al cerrar Bloque 1
python manage.py test rendiciones                # 69 OK al cerrar Bloque 2 (REN007)
```

Login: `/cuentas/login/`. Hay un superusuario de prueba `admin`/`admin`; el usuario también creó el suyo. No depender de esa clave.

---

## Agente y archivos de orquestación

| Qué | Dónde |
|-----|--------|
| Skill (reglas de construcción) | `.cursor/skills/nomina-sistema/SKILL.md` |
| Fórmulas Bloque 1 | `.cursor/skills/nomina-sistema/referencia-dominio.md` |
| Plan Bloque 2 | `.cursor/skills/nomina-sistema/referencia-bloque2-rendiciones.md` |
| Rule always-on | `.cursor/rules/nomina-sistema.mdc` |
| Bitácora (punto exacto) | `SEGUIMIENTO.md` |
| Este handoff | `CONTEXTO.md` |
| Mini-specs REM | `otros/mini-especificaciones/` + `otros/pdf/` |
| Mini-specs REN | `otros/mini-especificaciones/REN/` (+ PDF en `otros/pdf/`) |

Al retomar: **CONTEXTO.md → SEGUIMIENTO.md → skill → referencia-bloque2 → mini-spec REN00X**.

---

## Estado al corte (27 ago 2026)

**Cerrado:** infra + **Bloque 1** + **Bloque 2 (REN001–REN007)** + **FAC001–FAC007**.
**Siguiente:** **COM004 — IVA de compras**.

### Parches transversales

`MOD000` está aplicado como regla permanente del skill y de las reglas del proyecto. Antes de continuar con `COM004-R`, se debe ejecutar la secuencia `MOD001 → REM005-C01 → MOD002 → MOD003 → MOD004 → P01`.

`MOD001` también está aplicado: Remuneraciones fue revisado bajo la regla de hechos, derivados y snapshots. `REM005-C01` ya estaba implementado, con migración `remuneraciones.0008_pago_remuneracion_anulacion`; la suite `rrhh core remuneraciones` pasa con 138 tests. El siguiente parche es `MOD002`.

`MOD002` está aplicado: Rendiciones conserva entradas reales, calcula totales/cuadratura en servicios y usa acciones para los estados. La reapertura exige motivo desde la UI. La suite `rendiciones` pasa con 69 tests. El siguiente parche es `MOD003`.

`MOD003` está aplicado: Facturación mantiene separados hechos y derivados, bloquea cobros sobre documentos anulados y añade trazabilidad para anulación de cobros de ventas. La migración `facturacion.0003_cobro_venta_anulacion` está aplicada y la suite `facturacion` pasa con 22 tests. El siguiente parche es `MOD004`.

`MOD004` está aplicado: Compras mantiene cálculos y estados fuera de la entrada manual, excluye pagos anulados de saldos y exige motivo para anular documentos, bloqueando la anulación cuando existen pagos activos. La suite `facturacion` pasa con 22 tests. El siguiente parche es `P01`.

`P01` está concluido: se hizo revisión transversal de entradas, derivados, snapshots, estados y anulaciones en los módulos principales. Los formularios de Contratos y Obras ya no permiten editar directamente sus estados. La regresión `rrhh facturacion rendiciones` pasa con 113 tests; no quedan parches funcionales pendientes.

`COM004-R` está aplicado: `facturacion.services.iva_compras` agrega documentos de compra no anulados por período documental, proveedor, centro y tipo, con soporte de notas de crédito/débito, consistencia y salida documental para IMP. La suite `facturacion` pasa con 26 tests. El siguiente paso es `COM005-R`.

`COM005-R` está aplicado: `facturacion.services.reportes_compras` separa métricas documentales y pagos, calcula saldos actuales o a fecha de corte, agrupa resultados y prepara filas de exportación. Se agregó el resumen web con filtros GET. La suite `facturacion` pasa con 26 tests. El siguiente paso es `COM006-R`.

`COM006-R` está aplicado: `facturacion.services.integracion_compras` formaliza las salidas separadas hacia Impuestos (`DocumentoCompra`), Finanzas (`PagoDocumentoCompra`) y Excel, con identidad de origen para idempotencia y exclusión de anulados. El bloque COM queda cerrado y la suite `facturacion` pasa con 29 tests. El siguiente bloque es `IMP001`.

`IMP001` está aplicado: `PeriodoImpuesto` representa el mes tributario, calcula fechas derivadas y dispone de flujo controlado de validación, cierre y reapertura. La migración `impuestos.0002_periodo_validado` está aplicada y sus vistas básicas están disponibles bajo `/impuestos/periodos/`. El siguiente paso es `IMP002`.

`IMP002` está aplicado: `impuestos.iva` calcula los componentes documentales de IVA desde ventas y compras, con signos de notas, exclusión de anulados, detalles utilizados e inconsistencias. La suite de Impuestos pasa con 8 tests. El siguiente paso es `IMP003`.

`IMP003` está aplicado: `impuestos.ppm` calcula el PPM sobre el neto de ventas de IMP002, consulta `TASA_PPM` histórica y conserva el snapshot de tasa en `PeriodoImpuesto`. La suite de Impuestos pasa con 12 tests. El siguiente paso es `IMP004`.

`IMP004` está aplicado: `impuestos.determinacion` consolida IVA y PPM, exige los componentes previos, conserva resultados negativos y permite validar el período. La suite de Impuestos pasa con 15 tests. El siguiente paso es `IMP005`.

`IMP005` está aplicado: `impuestos.pagos` registra pagos reales parciales contra el monto de IMP004, calcula saldo/situación y soporta anulación auditable. La migración `impuestos.0003_pago_impuesto_auditoria` está aplicada y la suite de Impuestos pasa con 18 tests. El siguiente paso es `IMP006`.

`IMP006` está aplicado: `impuestos.reportes` entrega resúmenes por período y año, saldos tributarios, pagos por período/fecha y filas de exportación. El módulo IMP queda cerrado con 21 tests y el siguiente bloque puede ser Finanzas o la integración definida por el proyecto.

`FIN001` está aplicado: `CategoriaFinanciera` incluye `permite_manual`, el catálogo base está cargado por migración y las categorías automáticas quedan separadas de los movimientos manuales. Finanzas pasa 2 tests. El siguiente paso es `FIN002`.

`FIN002` está aplicado: `PagoRemuneracion` se integra como egreso financiero mediante `finanzas.integracion_remuneraciones`, con identidad idempotente y herencia de datos del origen. Finanzas pasa 3 tests. El siguiente paso es `FIN003`.

`FIN003` está aplicado: `CobroDocumentoTributario` se integra como ingreso financiero mediante `finanzas.integracion_facturacion`, usando fecha real de cobro, centro de costo heredado e identidad idempotente. Finanzas pasa 5 tests. El siguiente paso es `FIN004`.

`FIN004` está aplicado: `PagoDocumentoCompra` y `PagoImpuesto` se integran como egresos financieros idempotentes, excluyendo anulados y heredando los datos del origen. La categoría de rendiciones queda reservada porque REN no tiene aún un pago independiente. Finanzas pasa 6 tests. El siguiente paso es `FIN005`.

`FIN005` está aplicado: los movimientos manuales se registran únicamente con categorías activas autorizadas, se identifican como MANUAL y pueden anularse con auditoría. La migración `finanzas.0006_fin005_anulacion_manual` está aplicada y Finanzas pasa 9 tests. El siguiente paso es `FIN006`.

`FIN006` está aplicado: `finanzas.flujo` calcula flujo mensual, resultado, saldo inicial/final y agrupaciones por categoría/centro desde movimientos vigentes. Finanzas pasa 11 tests. El siguiente paso es `FIN007`.

`FIN007` está aplicado: `finanzas.anuales` reconstruye reportes anuales, matriz categoría/mes, acumulados, orígenes y salidas para BAL/Excel. El bloque FIN queda cerrado; la suite de Finanzas pasa 12 tests.

La interfaz general de Finanzas también está disponible: `/finanzas/movimientos/` lista movimientos con filtros y enlaza a la creación manual. El enlace `Finanzas` fue agregado al menú global.

| ID | Qué | Estado |
|----|-----|--------|
| REM001–010 | Remuneraciones completas | Hecho |
| REN001–007 | Rendiciones completas | **Hecho — Bloque 2 cerrado** |
| REN003 | Cuadratura | Pendiente |
| REN004 | Documentos / respaldos | Pendiente |
| REN005 | Flujo de estados | Pendiente |
| REN006 | Reportes / filtros | Pendiente |
| REN007 | Frontera Finanzas + Excel | Pendiente |
| FAC001 | Maestro de clientes | Hecho |
| FAC002 | Obras y centros de costo | Hecho |
| FAC003 | Documentos tributarios de venta | Hecho |
| FAC004 | Motor de cálculo tributario | Hecho |
| FAC005 | Cobros y estado de pago | Hecho |
| FAC006 | Consultas y reportes de facturación | Hecho |
| FAC007 | Integración con Impuestos, Finanzas y Excel | Hecho |
| COM001 | Maestro de proveedores | Hecho |
| COM002 | Documentos de compra | Hecho |
| COM003 | Pagos a proveedores | Hecho |
| COM004–006 | Compras restantes | Pendiente |

Modelos listos en `rendiciones/`: `Rendicion`, `RendicionDetalle`, `DocumentoRendicion`. Finanzas ya tiene FK a `Rendicion` (consumo futuro; no implementar en este bloque).

Migraciones Bloque 1: `rrhh` 0002, `core` 0002, `remuneraciones` 0007.

### Datos locales de prueba (se pueden dejar o borrar)

- Trabajador `ANA PRUEBA PEREZ` / `18.651.495-5` con contrato desde 01-01-2026 (cargo MAESTRO, CC EGC, sueldo 800.000)
- Período **Agosto 2026** con liquidación y costo
- Concepto `BONO_FAENA`

---

## Qué sigue (Bloque 2 en detalle)

1. **REN001** ✓ — CRUD cabecera; BORRADOR; anular borrador; 12 tests OK.
2. **REN002** ✓ — Formset de detalles; N líneas por CC; totales en ficha; 10 tests OK.
3. **REN003** ✓ — `validar_cuadratura()`; presentar solo si cuadra; 11 tests OK.
4. **REN004** ✓ — Documentos PDF/JPG/PNG; media por año/id; 7 tests OK.
5. **REN005** ✓ — Flujo de estados + permisos; motivo rechazo/anulación; 11 tests OK.
6. **REN006** ✓ — Filtros + resumen por CC/trabajador + `filas_exportacion`; 9 tests OK.
7. **REN007** ✓ — `datos_financieros()` / `filas_excel()`; frontera sin implementar Finanzas; 8 tests OK.

**Bloque 2 cerrado.** Siguiente: Facturación (bloque 3).

No priorizar `integracion_excel` global antes de cerrar REN: la spec del sistema pone Rendiciones antes que Excel de varios módulos.

## Bloque 1 — cerrado (no rehacer)

REM001–REM010: trabajadores, contratos, períodos, conceptos, HE, movimientos, finiquitos, liquidaciones, costos, resumen anual. Suite: **120 OK**.

---

## URLs útiles

| Área | URL |
|------|-----|
| Login | `/cuentas/login/` |
| Trabajadores | `/rrhh/trabajadores/` |
| Cargos / contratos | `/rrhh/cargos/`, `/rrhh/contratos/` |
| Períodos | `/remuneraciones/periodos/` |
| Horas extra | `/remuneraciones/horas-extra/` |
| Movimientos | `/remuneraciones/movimientos/` |
| Finiquitos | `/remuneraciones/finiquitos/` |
| Liquidaciones | `/remuneraciones/liquidaciones/` |
| Costos | `/remuneraciones/costos/` |
| Resumen anual | `/remuneraciones/resumen/` |
| Conceptos | `/remuneraciones/conceptos/` |
| Parámetros | `/parametros/` |
| Rendiciones | `/rendiciones/` |
| Admin | `/admin/` |

Nav en `templates/base.html`. Permisos por modelo Django (`view_` / `add_` / `change_`).

---

## Qué no hacer en el chat nuevo

- No rehacer REM001–010 ni volver a copiar `otros/modelos/`.
- No hardcodear `0.0079545` ni `0.19`.
- No crear modelos por mes/año ni columnas fijas CASA/EGC en rendiciones.
- No implementar Finanzas / IVA / asientos dentro de REN001–007.
- No saltar REN005 sin cuadratura (REN003).
- No commitear a menos que el usuario lo pida. No pushear a menos que lo pida.
- Verificar UI cuando se toquen pantallas.
- Al cerrar un módulo: actualizar `SEGUIMIENTO.md` y el Estado del skill.
