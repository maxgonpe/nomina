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

Siguiente tarea: REN002 — Distribución por centro de costo (Bloque 2).
Django es la fuente oficial. Reutilizar RendicionDetalle + CentroCosto.
UI en español (Chile). Bloque 1 y REN001 cerrados — no rehacerlos.
Orden Bloque 2: REN001 ✓ → 002 → 003 → 004 → 005 → 006 → 007.
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
python manage.py test rendiciones                # 12 OK al cerrar REN001
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

## Estado al corte (25 ago 2026)

**Cerrado:** infra + **Bloque 1** + **REN001**.  
**Siguiente:** **REN002 — Distribución por centro de costo**.

| ID | Qué | Estado |
|----|-----|--------|
| REM001–010 | Remuneraciones completas | Hecho |
| REN001 | Registro cabecera rendición | Hecho — `/rendiciones/` |
| REN002 | Distribución por CC | **Siguiente** |
| REN003 | Cuadratura | Pendiente |
| REN004 | Documentos / respaldos | Pendiente |
| REN005 | Flujo de estados | Pendiente |
| REN006 | Reportes / filtros | Pendiente |
| REN007 | Frontera Finanzas + Excel | Pendiente |

Modelos listos en `rendiciones/`: `Rendicion`, `RendicionDetalle`, `DocumentoRendicion`. Finanzas ya tiene FK a `Rendicion` (consumo futuro; no implementar en este bloque).

Migraciones Bloque 1: `rrhh` 0002, `core` 0002, `remuneraciones` 0007.

### Datos locales de prueba (se pueden dejar o borrar)

- Trabajador `ANA PRUEBA PEREZ` / `18.651.495-5` con contrato desde 01-01-2026 (cargo MAESTRO, CC EGC, sueldo 800.000)
- Período **Agosto 2026** con liquidación y costo
- Concepto `BONO_FAENA`

---

## Qué sigue (Bloque 2 en detalle)

1. **REN001** ✓ — CRUD cabecera; BORRADOR; anular borrador; 12 tests OK.
2. **REN002** — Formset de detalles; N líneas por CC; `total_distribuido`.
3. **REN003** — `validar_cuadratura()`; gate a PRESENTADA.
4. **REN004** — Uploads a media; tipos PDF/JPG/PNG.
5. **REN005** — Transiciones + permisos; motivo en rechazo/anulación.
6. **REN006** — Filtros; `resumen_por_centro`; `filas_exportacion()`.
7. **REN007** — `datos_financieros()` / `filas_excel()`; no implementar módulo Finanzas.

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
