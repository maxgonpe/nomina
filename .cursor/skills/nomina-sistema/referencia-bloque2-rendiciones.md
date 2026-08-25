# Referencia Bloque 2 — Rendiciones (REN001–REN007)

Fuente: `otros/mini-especificaciones/REN/` (docx) y PDF equivalentes en `otros/pdf/` (algunos PDF exportan casi vacíos; **mandan los docx**).

App: `rendiciones/`. Modelos ya existentes: `Rendicion`, `RendicionDetalle`, `DocumentoRendicion`. Reutilizar; no reinventar columnas CASA/EGC/CGA/OFI.

## Dependencia

```
REM001 Trabajador  →  Rendicion  →  RendicionDetalle  →  CentroCosto
```

Alimenta después: Finanzas, centros de costo, Contabilidad, Excel. **No** implementar Finanzas/IVA/asientos dentro de este bloque.

## Orden de construcción (obligatorio)

| # | ID | Qué | Entrega mínima |
|---|-----|-----|----------------|
| 1 | REN001 | Registro de rendición (cabecera) | CRUD listar/crear/editar/consultar; estado inicial BORRADOR; trabajador activo en alta |
| 2 | REN002 | Distribución por centro de costo | Detalles dinámicos (formset); N líneas por CC permitidas; total_distribuido |
| 3 | REN003 | Validación y cuadratura | `validar_cuadratura()`; solo cuadra → PRESENTADA; Decimal exacto |
| 4 | REN004 | Documentos y respaldos | `DocumentoRendicion`; media segura; PDF/JPG/PNG |
| 5 | REN005 | Flujo de aprobación | Estados + permisos presentar/aprobar/rechazar/anular; motivo en rechazo/anulación |
| 6 | REN006 | Consultas y reportes | Filtros año/mes/trabajador/CC/estado; resumen por centro; `filas_exportacion()` |
| 7 | REN007 | Preparación Finanzas + Excel | API interna idempotente: `datos_financieros()`, `filas_excel()`; solo APROBADA |

```
REN001 → REN002 → REN003 → REN004 → REN005 → REN006 → REN007
              └──────────────┘  (docs en paralelo tras cuadratura OK en diseño;
                                 en práctica: 003 luego 004)
```

## Estados (REN005)

`BORRADOR → PRESENTADA → APROBADA | RECHAZADA` (+ `PAGADA` vía Finanzas; `ANULADA`).

| Estado | Editar cabecera/detalles | Documentos | Aprobar |
|--------|--------------------------|------------|---------|
| BORRADOR | sí | sí | no |
| PRESENTADA | no | consulta | sí |
| APROBADA | no | consulta | no |
| RECHAZADA | no (hasta reabrir) | consulta | no |
| PAGADA / ANULADA | no | consulta | no |

Cuadratura (REN003) es gate de BORRADOR → PRESENTADA.

## Invariantes del bloque

- Centros de costo por FK / alias (`core.CentroCosto`), **nunca** columnas fijas CASA/EGC/…
- Dinero: `Decimal`; totales en `services/`, no en views ni solo en JS.
- Soft-delete / anulación: no borrar rendiciones avanzadas en el flujo.
- UI español Chile; fechas `dd-mm-yyyy`; permisos Django + mixins del Bloque 1.
- No modificar REM001–REM010.
- No meter balance, asientos, IVA, facturas, proveedores ni flujo de caja aquí.

## Estructura esperada al cerrar el bloque

```
rendiciones/
├── models.py          # ya existe
├── forms.py
├── views.py / urls.py
├── services/
│   ├── rendiciones.py   # alta, detalles, cuadratura
│   ├── estados.py       # transiciones
│   ├── reportes.py      # filtros, resumen, filas_exportacion
│   └── integracion.py   # datos_financieros, filas_excel (REN007)
├── templates/rendiciones/
├── static/rendiciones/js/
└── tests/
```

## Criterios de aceptación (resumen)

| ID | Listo cuando |
|----|----------------|
| REN001 | ✓ Crear/editar/listar/consultar/anular borrador |
| REN002 | ✓ Distribuir en N centros (varias líneas al mismo CC OK) |
| REN003 | ✓ Solo cuadrada puede presentarse |
| REN004 | ✓ Múltiples respaldos trazables en media |
| REN005 | ✓ Ninguna transición salta el flujo |
| REN006 | Totales Django reconstruyen la tabla Excel de rendiciones |
| REN007 | Salida normalizada a Finanzas/Excel sin conocer su interior |

## Roadmap posterior (contexto)

`Bloque 1 REM ✓ → Bloque 2 REN → Bloque 3 Facturación → 4 Impuestos → 5 Finanzas → 6 Contabilidad → 7 Integración Excel`
