# Seguimiento del desarrollo

Punto de corte: **24 de agosto de 2026**, al terminar **REM007**.

Al retomar: leer `CONTEXTO.md` (handoff), luego este archivo, el skill `.cursor/skills/nomina-sistema/SKILL.md` y la mini-especificación del siguiente ítem. **No rehacer** modelos ni REM001–REM004 ni REM006 ni REM007.

## Dónde estamos

| Ítem | Estado |
|------|--------|
| Infra Django (apps, settings, RUT, locale, media, migraciones, admin) | Hecho |
| REM001 Maestro de trabajadores | Hecho |
| REM002 Cargos, contratos y anexos | Hecho |
| REM003 Períodos de remuneración | Hecho |
| REM004 Conceptos y parámetros | Hecho |
| REM006 Horas extraordinarias | Hecho |
| REM007 Bonos, anticipos, préstamos y movimientos | Hecho — **último cerrado** |
| REM008 Finiquitos | **Siguiente** |
| REM005 Liquidación mensual (motor) | Pendiente (después de 003–004 y 006–008) |
| REM009 Costos mensuales por trabajador | Pendiente |
| REM010 Resumen anual y gráfico | Pendiente |

Orden obligatorio del Bloque 1 (no saltar a REM005):

`001 → 002 → 003 → 004 → 006 → 007 → 008 → 005 → 009 → 010`

Las mini-especificaciones están en `otros/mini-especificaciones/` (y PDF equivalentes en `otros/pdf/`). El análisis global está en `otros/pdf/analisis-del-sistema.pdf`. Los Excel origen: `otros/NOMINA REMUNERACIONES 2026.xlsx` y `otros/PLANILLA DE PAGOS GENERALES 2026.xlsx`.

Fuera del Bloque 1 (aún sin mini-specs de implementación): rendiciones, facturación, impuestos, finanzas, contabilidad, integración Excel. Los **modelos** de esas apps ya existen; no hay UI ni servicios.

## Qué quedó construido

### Infra

- Proyecto Django 5.2, SQLite, venv en `.env/`
- Apps en `INSTALLED_APPS`: `core`, `rrhh`, `remuneraciones`, `rendiciones`, `facturacion`, `impuestos`, `finanzas`, `contabilidad`, `integracion_excel`
- Locale `es-cl`, zona `America/Santiago`, fechas `dd-mm-yyyy`
- `core/validators.py`: RUT (normalizar, validar DV, formatear)
- Admin de todas las apps
- Migraciones aplicadas (`rrhh` hasta `0002`, `core` hasta `0002`, `remuneraciones` hasta `0004`)

### REM001 — Trabajadores

- CRUD + desactivación (no borra)
- RUT único y con dígito verificador
- Rutas: `/rrhh/trabajadores/`
- Tests: `rrhh/tests.py`, `core/tests.py`

### REM002 — Cargos, contratos, anexos

- CRUD de cargos: `/rrhh/cargos/`
- Contratos y anexos: `/rrhh/contratos/`
- En la ficha del trabajador: línea de tiempo y consulta de condición a una fecha (sueldo, cargo, centro de costo)
- Servicio: `rrhh/services/contratos.py` → `condicion_vigente(trabajador, fecha)`
- Validaciones: sueldo > 0, término ≥ inicio, anexos dentro del contrato, sin contratos solapados, sin anexos contradictorios en la misma fecha
- Archivos de anexo en `media/rrhh/anexos/<año>/<id_trabajador>/` con nombre sanitizado
- Tests: `rrhh/test_contratos.py`

### REM003 — Períodos de remuneración

- Listado, alta y ficha: `/remuneraciones/periodos/`
- Fechas de inicio/fin derivadas del mes (p. ej. 08/2026 → 01-08-2026 a 31-08-2026)
- Estados: `BORRADOR → ABIERTO → CALCULADO → VALIDADO → CERRADO`
- Cierre vía `remuneraciones/services/periodos.py` → `cerrar()` (transacción). No cierra si hay liquidaciones en borrador o sin recálculo
- Período cerrado bloquea HE, movimientos, liquidaciones y finiquitos
- Reapertura a ABIERTO con motivo obligatorio (auditoría: `motivo_reapertura`, se conserva el último cierre)
- Una hoja Excel (SEPTIEMBRE, etc.) no abre el período; `nombre_hoja_excel` es solo la equivalencia
- Tests: `remuneraciones/test_periodos.py`

### REM004 — Conceptos y parámetros

- Conceptos: `/remuneraciones/conceptos/` (haber/descuento/informativo). Un concepto nuevo no agrega columnas a `LiquidacionMensual`
- Catálogo inicial: SUELDO_BASE, HORAS_EXTRA, AGUINALDO, COLACION, ANTICIPO, etc.
- Parámetros con vigencia: `/parametros/` (`ParametroNegocio` + `ParametroValor`)
- Servicio: `core/services/parametros.py` → `valor("FACTOR_HE", fecha)` y `valor_hora_extra(sueldo, fecha)`. No hardcodear `0.0079545`
- FACTOR_HE 2026 = 0.0079545 (01-01-2026 a 31-12-2026). También definidos VALOR_COLACION_MENSUAL, VALOR_MOVILIZACION_MENSUAL, VALOR_DESGASTE_HERRAMIENTAS (sin monto hasta cargarlos)
- Tests: `remuneraciones/test_conceptos.py`, `core/test_parametros.py`

### REM006 — Horas extraordinarias

- Listado y filtros: `/remuneraciones/horas-extra/`
- Carga rápida en el período (varias filas, sin salir): `/remuneraciones/periodos/<id>/horas-extra/`
- Por trabajador: `/remuneraciones/trabajadores/<id>/horas-extra/`
- Servicio: `suma_horas_extra(trabajador, periodo)` — insumo oficial de REM005 (no se guardan las horas a mano en la liquidación)
- Fecha dentro del período; horas > 0; período cerrado no crea/edita/borra
- Cambiar HE en período abierto marca la liquidación `requiere_recalculo=True` (no recalcula montos aquí)
- Import/export Excel de la tabla inferior queda para `integracion_excel`
- Tests: `remuneraciones/test_horas_extra.py`

### REM007 — Bonos, anticipos, préstamos y movimientos

- Listado y filtros: `/remuneraciones/movimientos/`
- Carga rápida en el período: `/remuneraciones/periodos/<id>/movimientos/`
- Por trabajador: `/remuneraciones/trabajadores/<id>/movimientos/`
- Servicio: `remuneraciones/services/movimientos.py` → `registrar_movimiento()`, `suma_movimientos(trabajador, periodo, tipo)`
- El signo lo da `concepto.tipo` (haber/descuento); el monto siempre es positivo
- Origen por defecto `MANUAL`. `CALCULADO` / `IMPORTADO_EXCEL` quedan para el motor y la integración
- Si no hay liquidación, se abre un **borrador** con el contrato vigente (los totales los calcula REM005)
- Un concepto nuevo (p. ej. BONO_FAENA) no agrega columnas a `LiquidacionMensual`
- Catálogo explícito de préstamos: `PRESTAMO_ENTREGADO` (haber) y `PRESTAMO_DESCUENTO` (descuento)
- SUELDO_BASE, HORAS_EXTRA, FINIQUITO e INASISTENCIA no se cargan a mano
- Período cerrado o movimiento `bloqueado` no crea/edita/borra; cambia el movimiento y marca `requiere_recalculo`
- Colación/movilización/desgaste automáticos: en REM005, no aquí
- Import a columnas Excel: `integracion_excel`
- Tests: `remuneraciones/test_movimientos.py`

## Cómo retomar

```bash
cd /home/maxgonpe/nomina
source .env/bin/activate
python manage.py runserver 127.0.0.1:8000
```

- Login: [http://127.0.0.1:8000/cuentas/login/](http://127.0.0.1:8000/cuentas/login/)
- Usar el superusuario que ya creaste (hay además un `admin`/`admin` de prueba; conviene no depender de esa clave)
- Tests: `python manage.py test rrhh core remuneraciones`

Primera tarea al volver: **REM008 — Finiquitos**.

1. Leer `otros/mini-especificaciones/` (REM008 / finiquitos).
2. Reutilizar `Finiquito`; alimentar la liquidación sin duplicar al recalcular (REM005).
3. No empezar el motor de liquidación hasta cerrar REM008.
4. Actualizar la tabla de este archivo al cerrar REM008.

## Qué no hacer al retomar

- No volver a copiar modelos desde `otros/modelos/` (ya están en las apps).
- No crear un modelo por mes o por año.
- No hardcodear `FACTOR_HE` ni otras tasas; ya están en parámetros (`valor("FACTOR_HE", fecha)`).
- No empezar el motor de liquidación (REM005) hasta tener 003, 004, 006, 007 y 008.
