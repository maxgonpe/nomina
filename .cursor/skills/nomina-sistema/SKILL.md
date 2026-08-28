---
name: nomina-sistema
description: >-
  Orquesta la construcción del sistema Django de nómina, remuneraciones, rrhh,
  rendiciones, facturación, impuestos, finanzas y Excel para Sistemas Hídricos.
  Use when implementing REM001-REM010, REN001-REN007, liquidaciones, rendiciones,
  trabajadores, centros de costo, horas extra, finiquitos, o al continuar el
  sistema a partir de las mini-especificaciones y planillas Excel.
---

# Sistema de nómina (Sistemas Hídricos)

Django es la fuente oficial. Excel es plantilla de importación/exportación, nunca el maestro.

Antes de implementar un módulo, leer la mini-especificación y los modelos ya existentes en la app. No reinventar modelos que ya están.

- Bloque 1 (fórmulas REM): [referencia-dominio.md](referencia-dominio.md)
- Bloque 2 (plan REN): [referencia-bloque2-rendiciones.md](referencia-bloque2-rendiciones.md)

## Apps (no fusionar, no renombrar)

| App | Dominio |
|-----|---------|
| `core` | Auditoría, centros de costo, alias, parámetros con vigencia, RUT |
| `rrhh` | Trabajador, cargo, contrato, anexo |
| `remuneraciones` | Período, conceptos, liquidación, HE, movimientos, finiquito, costos |
| `rendiciones` | Rendición y detalle por centro de costo |
| `facturacion` | Cliente, obra, DTE, proveedor, compras |
| `finanzas` | Categorías, movimientos, caja, obligaciones |
| `impuestos` | IVA / PPM por período |
| `contabilidad` | Cuentas y asientos (el balance es un reporte) |
| `integracion_excel` | Plantillas, mapeos, import/export |

## Invariantes

### Regla funcional transversal (MOD000)

- **ENTRADA:** hecho que el usuario conoce y registra, como fechas, personas, documentos, horas y pagos.
- **DERIVADO:** valor que Django obtiene inequívocamente, como IVA, totales, saldos, cuadratura, estados de pago y reportes.
- **SNAPSHOT:** valor calculado u obtenido por Django que debe conservarse históricamente, como tasas, sueldo, cargo y centro de costo usados en un cálculo.
- Si un dato puede deducirse inequívocamente desde información oficial, no se solicita nuevamente.
- Los derivados se calculan en `services/`; no se aceptan como autoridad desde formularios, templates, JavaScript o Excel.
- Los snapshots los genera Django y no se editan manualmente ni se reescriben retroactivamente.
- Los estados matemáticamente deducibles se derivan; las decisiones de flujo se ejecutan mediante acciones explícitas.
- Los agregados mensuales y anuales son reportes sobre hechos almacenados, no entradas manuales.

- No crear modelos por mes/año (`NominaAgosto`, `Gastos2026`). Usar período + fecha.
- No poner aguinaldo/bono/colación como columnas fijas en `LiquidacionMensual`. Son `ConceptoRemuneracion` + `MovimientoRemuneracion`.
- No poner CASA/EGC/CGA/OFI como columnas en rendiciones. Son filas `RendicionDetalle` → `CentroCosto`.
- Factores (`FACTOR_HE`, IVA, PPM, colación, movilización, desgaste) viven en `ParametroNegocio` / `ParametroValor`. Nunca hardcodear `0.0079545` ni `0.19` en servicios.
- Liquidaciones cerradas guardan snapshots (sueldo, cargo, centro de costo). Un anexo posterior no reescribe enero.
- Relacionar por FK (`trabajador_id`, RUT normalizado). Nunca por nombre.
- Cálculo oficial en `services/`, no en `views.py` ni en Excel.
- Dinero y tasas: `Decimal`, nunca `float`.
- RUT: validar DV y guardar `rut_normalizado` único.
- Soft-delete: `activo=False`; no borrar históricos.
- UI y mensajes en español (Chile). Fechas `dd-mm-yyyy`. Zona `America/Santiago`.
- No commitear `otros/` ni `.xlsx` (están en `.gitignore`).
- Bloque 2 no implementa Finanzas, IVA, asientos ni facturas (REN007 solo prepara interfaces).

## Orden de construcción

Infra primero. Luego bloques:

### Bloque 1 — Remuneraciones (cerrado)

`REM001 → 002 → 003 → 004 → 006 → 007 → 008 → 005 → 009 → 010`

### Bloque 2 — Rendiciones (cerrado)

`REN001 → 002 → 003 → 004 → 005 → 006 → 007`

Specs: `otros/mini-especificaciones/REN/` (docx). PDF en `otros/pdf/` como respaldo (algunos casi vacíos).

### Después

Facturación → Impuestos → Finanzas → Contabilidad → Integración Excel.

## Cómo implementar cada ítem (REM / REN)

1. Leer la mini-spec correspondiente (`otros/mini-especificaciones/…`).
2. Reutilizar modelos existentes; cambiarlos solo si la spec lo exige.
3. Capa: `services/` para reglas, `forms.py` + CBV para UI, `admin.py` operativo.
4. Tests del criterio de aceptación de la spec.
5. No dejar TODOs vacíos del alcance de ese ítem.
6. Actualizar `SEGUIMIENTO.md` al cerrar.

## Stack

Django 5.2, SQLite ahora (diseñar para PostgreSQL después), Bootstrap + Chart.js en UI, openpyxl para Excel más adelante.

## Estado

Bitácora: [`SEGUIMIENTO.md`](../../../SEGUIMIENTO.md). Handoff: [`CONTEXTO.md`](../../../CONTEXTO.md).

Corte: **Bloque 1 + Bloque 2 (REN001–REN007) cerrados**. **Siguiente: Bloque 3 (Facturación)** cuando haya mini-specs.
