# Referencia de dominio

Fuente: `otros/analisis-del-sistema.md`, mini-especificaciones REM001–REM010, `otros/modelos/`, y los Excel de `otros/`.

## Excel origen

**NOMINA REMUNERACIONES 2026.xlsx** — una hoja por mes (ene–dic) + RESUMEN 2026. Cada mes tiene tres tablas: liquidación, horas extra, costo trabajador. Columnas variables entre meses. Identidad hoy: nombre + C.I.

**PLANILLA DE PAGOS GENERALES 2026.xlsx** — gastos anuales, rendiciones por centro (CASA/EGC/CGA/OFI), facturación, impuestos, balance, cobranzas laborales mezcladas en la hoja 2026. Sueldos se alimentan desde la nómina por vínculo externo.

Una hoja Excel existente no implica período abierto. Sep–dic 2026 son plantilla.

## Fórmulas oficiales (Bloque 1)

Leer parámetros vigentes por fecha; no copiar literales.

| Concepto | Fórmula |
|----------|---------|
| Valor día | `sueldo_base_snapshot / 30` |
| Días trabajados | `30 - dias_fallados` |
| Valor HE | `sueldo_base_snapshot * FACTOR_HE` |
| Monto HE | `horas_extra_total * valor_hora_extra` |
| HE del mes | `SUM(HoraExtra.horas)` del trabajador en el período |
| Haberes | sueldo base + movimientos tipo HABER (incluye HE y finiquito si aplica) |
| Descuentos | SUM movimientos tipo DESCUENTO (anticipos, préstamos, inasistencia) |
| Total liquidado | haberes − descuentos |
| Total a pagar | total liquidado (salvo regla explícita posterior) |
| Saldo | total_a_pagar − SUM(PagoRemuneracion) |
| Proporcional (colación, mov, desgaste) | `dias_trabajados * (valor_mensual / 30)` |

`FACTOR_HE` histórico en Excel ≈ `0.0079545`. IVA 19% y PPM con vigencia por período.

## Estados

Período: `BORRADOR → ABIERTO → CALCULADO → VALIDADO → CERRADO` (reapertura auditada).

Liquidación: `BORRADOR → CALCULADA → VALIDADA → PAGADA → CERRADA` (+ `ANULADA`).

Cerrado: no editar HE, movimientos, finiquitos ni recalcular, salvo reapertura.

## Centros de costo vistos en Excel

OFC / OFI / OFICINA CENTRAL, EGC, CASA, CGA, obras. Homologar con `AliasCentroCosto`, no crear un centro por cada alias.

## Modelos clave ya existentes

- `core`: `AuditModel`, `CentroCosto`, `AliasCentroCosto`, `ParametroNegocio`, `ParametroValor`
- `rrhh`: `Trabajador`, `Cargo`, `Contrato`, `AnexoContrato`
- `remuneraciones`: `PeriodoRemuneracion`, `ConceptoRemuneracion`, `LiquidacionMensual`, `MovimientoRemuneracion`, `HoraExtra`, `PagoRemuneracion`, `Finiquito`, `ConceptoCostoTrabajador`, `CostoTrabajadorPeriodo`, `CostoTrabajadorDetalle`

Nombres canónicos: los de `*/models.py`, no los del análisis (a veces dice `Trabajador`/`PeriodoRemuneracion` de forma genérica).

## Criterios REM (aceptación mínima)

| ID | Listo cuando |
|----|----------------|
| REM001 | CRUD trabajador, RUT único y válido, desactivar sin borrar histórico |
| REM002 | Dada una fecha: contrato, cargo, CC y sueldo vigentes (anexos) |
| REM003 | Períodos independientes del Excel; cierre bloquea cambios |
| REM004 | Nuevo haber/descuento sin alterar columnas de `LiquidacionMensual` |
| REM006 | Suma HE = insumo de REM005; fecha dentro del período |
| REM007 | Movimientos por concepto; origen MANUAL/CALCULADO/IMPORTADO |
| REM008 | Finiquito propio; alimenta liquidación sin duplicar al recalcular |
| REM005 | Django reproduce la liquidación del Excel con snapshots y servicios |
| REM009 | Costo generado desde liquidación, snapshot de CC |
| REM010 | Resumen anual por consulta (no modelo ene–dic); Chart.js |

Cada mini-spec en `otros/mini-especificaciones/` manda sobre este resumen.
