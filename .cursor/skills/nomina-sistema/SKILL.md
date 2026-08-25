---
name: nomina-sistema
description: >-
  Orquesta la construcción del sistema Django de nómina, remuneraciones, rrhh,
  rendiciones, facturación, impuestos, finanzas y Excel para Sistemas Hídricos.
  Use when implementing REM001-REM010, liquidaciones, trabajadores, centros de
  costo, horas extra, finiquitos, o al continuar el sistema a partir de las
  mini-especificaciones y planillas Excel.
---

# Sistema de nómina (Sistemas Hídricos)

Django es la fuente oficial. Excel es plantilla de importación/exportación, nunca el maestro.

Antes de implementar un módulo, leer la mini-especificación en `otros/mini-especificaciones/` y los modelos ya existentes en la app. No reinventar modelos que ya están.

Detalle de fórmulas, mapeo Excel y criterios REM: [referencia-dominio.md](referencia-dominio.md).

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

- No crear modelos por mes/año (`NominaAgosto`, `Gastos2026`). Usar período + fecha.
- No poner aguinaldo/bono/colación como columnas fijas en `LiquidacionMensual`. Son `ConceptoRemuneracion` + `MovimientoRemuneracion`.
- Factores (`FACTOR_HE`, IVA, PPM, colación, movilización, desgaste) viven en `ParametroNegocio` / `ParametroValor`. Nunca hardcodear `0.0079545` ni `0.19` en servicios.
- Liquidaciones cerradas guardan snapshots (sueldo, cargo, centro de costo). Un anexo posterior no reescribe enero.
- Relacionar por FK (`trabajador_id`, RUT normalizado). Nunca por nombre.
- Cálculo oficial en `services/`, no en `views.py` ni en Excel.
- Dinero y tasas: `Decimal`, nunca `float`.
- RUT: validar DV y guardar `rut_normalizado` único.
- Soft-delete: `activo=False`; no borrar históricos.
- UI y mensajes en español (Chile). Fechas `dd-mm-yyyy`. Zona `America/Santiago`.
- No commitear `otros/` ni `.xlsx` (están en `.gitignore`).

## Orden de construcción

Infra primero (settings, validators, apps registradas, migraciones, admin). Luego Bloque 1 en este orden:

1. REM001 Trabajadores
2. REM002 Cargos / contratos / anexos
3. REM003 Períodos
4. REM004 Conceptos y parámetros
5. REM006 Horas extra
6. REM007 Movimientos
7. REM008 Finiquitos
8. REM005 Motor de liquidación
9. REM009 Costos
10. REM010 Resumen anual

No adelantar REM005 con datos simulados si faltan 001–004 y 006–008.

## Cómo implementar cada REM

1. Leer `otros/mini-especificaciones/REM00X*.md` (o `.docx`/`.pdf` equivalentes).
2. Reutilizar modelos existentes; cambiarlos solo si la spec lo exige.
3. Capa: `services/` para reglas, `forms.py` + CBV para UI, `admin.py` operativo.
4. Tests del criterio de aceptación de la spec.
5. No dejar TODOs vacíos del alcance de esa REM.

## Stack

Django 5.2, SQLite ahora (diseñar para PostgreSQL después), Bootstrap + Chart.js en UI, openpyxl para Excel más adelante.

## Estado

La bitácora viva está en [`SEGUIMIENTO.md`](../../../SEGUIMIENTO.md). El handoff para un chat nuevo está en [`CONTEXTO.md`](../../../CONTEXTO.md).

Corte actual: REM005 cerrado. Siguiente: REM009 (costos mensuales por trabajador).
