# Seguimiento del desarrollo

Punto de corte: **24 de agosto de 2026**, al terminar **REM002**.

Al retomar: leer este archivo, luego el skill `.cursor/skills/nomina-sistema/SKILL.md` y la mini-especificación del siguiente ítem. **No rehacer** modelos ni REM001/REM002.

## Dónde estamos

| Ítem | Estado |
|------|--------|
| Infra Django (apps, settings, RUT, locale, media, migraciones, admin) | Hecho |
| REM001 Maestro de trabajadores | Hecho |
| REM002 Cargos, contratos y anexos | Hecho — **último cerrado** |
| REM003 Períodos de remuneración | **Siguiente** |
| REM004 Conceptos y parámetros | Pendiente |
| REM006 Horas extraordinarias | Pendiente |
| REM007 Bonos, anticipos, préstamos y movimientos | Pendiente |
| REM008 Finiquitos | Pendiente |
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
- Migraciones aplicadas (`rrhh` hasta `0002`)

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

## Cómo retomar

```bash
cd /home/maxgonpe/nomina
source .env/bin/activate
python manage.py runserver 127.0.0.1:8000
```

- Login: [http://127.0.0.1:8000/cuentas/login/](http://127.0.0.1:8000/cuentas/login/)
- Usar el superusuario que ya creaste (hay además un `admin`/`admin` de prueba; conviene no depender de esa clave)
- Tests: `python manage.py test rrhh core`

Primera tarea al volver: **REM003 — Períodos de remuneración**.

1. Leer `otros/mini-especificaciones/` (REM003 / períodos).
2. Reutilizar `remuneraciones.PeriodoRemuneracion` (el modelo ya está).
3. Implementar estados, apertura/cierre, bloqueo al cerrado, tests.
4. Actualizar la tabla de este archivo al cerrar REM003.

## Qué no hacer al retomar

- No volver a copiar modelos desde `otros/modelos/` (ya están en las apps).
- No crear un modelo por mes o por año.
- No hardcodear `FACTOR_HE` ni otras tasas; irán en parámetros (REM004).
- No empezar el motor de liquidación (REM005) hasta tener 003, 004, 006, 007 y 008.
