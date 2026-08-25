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
4. La mini-especificación del siguiente ítem en otros/mini-especificaciones/ (o otros/pdf/)

Siguiente tarea: REM010 — Resumen anual y gráfico.
Django es la fuente oficial. Reutilizar modelos existentes. UI en español (Chile).
```

---

## Qué es el proyecto

Reemplazar dos libros Excel como fuente de verdad por un sistema Django para **Sistemas Hídricos**. Excel queda como importación/exportación, nunca como maestro.

**Excel origen** (en `otros/`, gitignored):

| Libro | Contenido |
|-------|-----------|
| `NOMINA REMUNERACIONES 2026.xlsx` | Una hoja por mes (ene–dic) + RESUMEN 2026. Cada mes: 3 tablas (liquidación, horas extra, costo trabajador). Columnas variables entre meses. Identidad hoy: nombre + C.I. |
| `PLANILLA DE PAGOS GENERALES 2026.xlsx` | Gastos, rendiciones por centro (CASA/EGC/CGA/OFI), facturación, impuestos, balance. Los sueldos se alimentan desde la nómina. |

Sep–dic 2026 en el Excel son **plantilla**. Tener la hoja no significa que el período esté abierto.

**Especificaciones:** `otros/mini-especificaciones/` (docx) y `otros/pdf/`. Análisis: `otros/pdf/analisis-del-sistema.pdf`. Modelos de referencia ya copiados a las apps: `otros/modelos/`.

---

## Conclusiones del análisis

1. **No modelar el Excel.** No hay `NominaAgosto` ni columnas fijas por bono/aguinaldo/colación. Un mes es un `PeriodoRemuneracion` (año + mes). Un haber/descuento nuevo es un `ConceptoRemuneracion` + `MovimientoRemuneracion`.
2. **Identidad por RUT**, no por nombre. Validar dígito verificador; guardar `rut_normalizado` único.
3. **Parámetros con vigencia.** `FACTOR_HE` (histórico 2026 = `0.0079545`), IVA, PPM, colación, movilización, desgaste: `ParametroNegocio` + `ParametroValor`. Nunca hardcodear en servicios. Consultar `valor("FACTOR_HE", fecha)`.
4. **Snapshots en liquidación.** Sueldo, cargo y centro de costo se congelan al calcular. Un anexo de mayo no reescribe enero.
5. **Centros de costo por alias.** OFC/OFI/OFICINA CENTRAL son el mismo centro. Homologar con `AliasCentroCosto`.
6. **Cálculo en `services/`**, no en views ni en Excel. Dinero y tasas: `Decimal`.
7. **Soft-delete:** `activo=False`. No borrar históricos.
8. **REM005 (motor)** usa insumos reales de HE, movimientos y finiquitos. No hardcodear factores ni columnas por concepto.
9. **REM009** genera costos desde la liquidación ya calculada (snapshot de CC).

Fórmulas oficiales (Bloque 1): ver `.cursor/skills/nomina-sistema/referencia-dominio.md`.

---

## Decisiones y diseño a seguir

### Apps (no fusionar, no renombrar)

`core` · `rrhh` · `remuneraciones` · `rendiciones` · `facturacion` · `impuestos` · `finanzas` · `contabilidad` · `integracion_excel`

Los modelos de todas las apps **ya existen**. Fuera del Bloque 1 no hay UI ni servicios todavía.

### Orden del Bloque 1

`REM001 → 002 → 003 → 004 → 006 → 007 → 008 → 005 → 009 → 010`

### Capa de implementación (patrón ya usado)

1. Leer la mini-spec del REM.
2. Reutilizar el modelo; cambiarlo solo si la spec lo exige.
3. Reglas en `services/`. UI: `forms.py` + CBV (`LoginRequiredMixin` + `PermissionRequiredMixin` + `AuditFormMixin`).
4. Templates Bootstrap 5 en `templates/`, español Chile, fechas `dd-mm-yyyy`.
5. Tests del criterio de aceptación.
6. Al cerrar el REM: actualizar `SEGUIMIENTO.md`.

### Invariantes (no negociar)

- Django maestro; Excel plantilla.
- Período + fecha; nunca un modelo por mes/año.
- Conceptos variables no son columnas de `LiquidacionMensual`.
- Período cerrado bloquea HE, movimientos, liquidaciones y finiquitos (salvo reapertura con motivo).
- Relacionar por FK / RUT normalizado, nunca por nombre.
- No commitear `otros/` ni `.xlsx`.

### Stack

Django 5.2.17, SQLite ahora (diseñar para PostgreSQL), venv en `.env/`, locale `es-cl`, zona `America/Santiago`, Bootstrap 5, Chart.js más adelante (REM010), openpyxl más adelante (integración Excel).

### Cómo levantar

```bash
cd /home/maxgonpe/nomina
source .env/bin/activate
python manage.py runserver 127.0.0.1:8000
python manage.py test rrhh core remuneraciones   # 110 OK al cerrar REM009
```

Login: `/cuentas/login/`. Hay un superusuario de prueba `admin`/`admin`; el usuario también creó el suyo. No depender de esa clave.

---

## Agente y archivos de orquestación

| Qué | Dónde |
|-----|--------|
| Skill (reglas de construcción) | `.cursor/skills/nomina-sistema/SKILL.md` |
| Fórmulas y criterios REM | `.cursor/skills/nomina-sistema/referencia-dominio.md` |
| Rule always-on | `.cursor/rules/nomina-sistema.mdc` |
| Bitácora (punto exacto) | `SEGUIMIENTO.md` |
| Este handoff | `CONTEXTO.md` |
| Mini-specs | `otros/mini-especificaciones/` y `otros/pdf/` |

Al retomar: **CONTEXTO.md → SEGUIMIENTO.md → skill → mini-spec del siguiente REM**.

---

## Estado al corte (25 ago 2026)

**Cerrado:** infra + REM001–009 (Bloque 1 casi completo).  
**Siguiente:** **REM010** (resumen anual y gráfico).

| ID | Qué | Rutas / servicios clave |
|----|-----|-------------------------|
| Infra | Apps, RUT, locale, migraciones, admin, login | `/cuentas/login/`, `/admin/` |
| REM001 | Trabajadores CRUD, desactivar sin borrar | `/rrhh/trabajadores/` |
| REM002 | Cargos, contratos, anexos; condición a una fecha | `/rrhh/cargos/`, `/rrhh/contratos/`; `condicion_vigente()` |
| REM003 | Períodos independientes del Excel; cierre bloquea | `/remuneraciones/periodos/`; `cerrar()` / `reabrir()` |
| REM004 | Conceptos + parámetros con vigencia | `/remuneraciones/conceptos/`, `/parametros/`; `valor()` |
| REM006 | HE; suma = insumo REM005 | `/remuneraciones/horas-extra/`; `suma_horas_extra()` |
| REM007 | Movimientos por concepto; signo = tipo | `/remuneraciones/movimientos/`; `registrar_movimiento()`, `suma_movimientos()` |
| REM008 | Finiquito propio; alimenta FINIQUITO sin duplicar | `/remuneraciones/finiquitos/`; `validar()`, `sincronizar_movimiento_finiquito()` |
| REM005 | Motor de liquidación; snapshots; pagos | `/remuneraciones/liquidaciones/`; `calcular()`, `calcular_periodo()` |
| REM009 | Costo desde liquidación; snapshot CC | `/remuneraciones/costos/`; `generar_desde_liquidacion()` |

Migraciones aplicadas: `rrhh` 0002, `core` 0002, `remuneraciones` 0007.

Catálogo inicial de conceptos: SUELDO_BASE, HORAS_EXTRA, AGUINALDO, ALOJAMIENTO, MOVILIZACION, COLACION, DESGASTE_HERRAMIENTAS, BONO_PRODUCCION, BONO_ASISTENCIA, FINIQUITO, ANTICIPO, PRESTAMO_ENTREGADO, PRESTAMO_DESCUENTO, INASISTENCIA. En verificación UI existe además **BONO_FAENA** (un haber nuevo no toca `LiquidacionMensual`).

`FACTOR_HE` 2026: `0.0079545` (01-01-2026 a 31-12-2026). Colación/movilización/desgaste existen como parámetros **sin monto** hasta cargarlos (el motor los omite si no hay vigencia).

### Datos locales de prueba (se pueden dejar o borrar)

- Trabajador `ANA PRUEBA PEREZ` / `18.651.495-5` con contrato desde 01-01-2026 (cargo MAESTRO, CC EGC, sueldo 800.000)
- Período **Agosto 2026** (CALCULADO) con horas extra, movimientos y finiquito validado
- Liquidación **validada** de ANA; costo generado (snapshot EGC)
- Concepto `BONO_FAENA`

---

## REM010 — qué hay que hacer al retomar

Mini-spec: `otros/pdf/REM010 — Resumen anual y gráfico.pdf`.

- Resumen anual por consulta (no modelo ene–dic).
- Chart.js en UI.
- Usar liquidaciones/costos existentes; no reinventar el motor.

## REM009 — ya cerrado (no rehacer)

- `CostoTrabajadorPeriodo` 1:1 con liquidación; detalle por `ConceptoCostoTrabajador`.
- Auto al `calcular()`; snapshot de CC; TOTAL_LIQUIDADO informativo.
- Totales por centro: `totales_por_centro(periodo)` (insumo futuro de finanzas).

## REM005 — ya cerrado (no rehacer)

- Motor en `remuneraciones/services/liquidaciones.py`.
- Snapshots; HE vía `valor_hora_extra`; proporcionales si hay parámetro; finiquito sin duplicar; pagos reales para PAGADA.
- UI: listado/detalle, calcular desde período, días fallados, validar/anular/pagar.
- Al calcular también genera/actualiza el costo (REM009).

## REM008 — ya cerrado (no rehacer)

- Entidad `Finiquito` (BORRADOR → VALIDADO → PAGADO / ANULADO). PDF en media.
- Validar genera un movimiento FINIQUITO CALCULADO y bloqueado. Sincronizar de nuevo no duplica.
- `terminar_contrato(contrato, fecha)` es explícito; validar no cierra el contrato.

## REM007 — ya cerrado (no rehacer)

- `MovimientoRemuneracion` cuelga de `LiquidacionMensual`. Si no hay liquidación, `obtener_o_crear_liquidacion_borrador()` abre un borrador con el contrato vigente.
- Sin contrato vigente en el período no se puede registrar el movimiento.
- Signo = `concepto.tipo`. Monto absoluto. Préstamos: `PRESTAMO_ENTREGADO` (haber) vs `PRESTAMO_DESCUENTO` (descuento).
- Manuales: BONO_*, AGUINALDO, ANTICIPO, ALOJAMIENTO. No a mano: SUELDO_BASE, HORAS_EXTRA, FINIQUITO, INASISTENCIA.
- Automáticos COLACION/MOVILIZACION/DESGASTE: los genera REM005.
- Origen MANUAL en la UI. Import Excel: `integracion_excel`.

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
| Conceptos | `/remuneraciones/conceptos/` |
| Parámetros | `/parametros/` |
| Admin | `/admin/` |

Nav en `templates/base.html`. Permisos por modelo Django (`view_` / `add_` / `change_`).

---

## Qué no hacer en el chat nuevo

- No rehacer REM001–009 ni volver a copiar `otros/modelos/`.
- REM010 es el siguiente (último del Bloque 1).
- No hardcodear `0.0079545` ni `0.19`.
- No crear modelos por mes/año ni columnas de bono en la liquidación.
- No commitear a menos que el usuario lo pida. No pushear a menos que lo pida.
- Verificar UI en el navegador cuando se toque pantallas (o tests + curl si no hay browser).
- Al cerrar un REM: actualizar `SEGUIMIENTO.md` y la sección Estado del skill.
