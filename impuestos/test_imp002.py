from datetime import date
from decimal import Decimal
from django.test import TestCase
from core.models import CentroCosto
from facturacion.models import Cliente, DocumentoCompra, DocumentoTributario, Proveedor
from impuestos.iva import calcular_iva_periodo, inconsistencias_iva
from impuestos.models import PeriodoImpuesto


class IMP002Tests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(rut="18.651.495-5", razon_social="Cliente IVA")
        self.proveedor = Proveedor.objects.create(rut="17.222.333-4", razon_social="Proveedor IVA")
        self.cc = CentroCosto.objects.create(codigo="CC-IVA", nombre="IVA")
        self.periodo = PeriodoImpuesto.objects.create(anio=2026, mes=8)

    def test_calcula_iva_ventas_y_compras_sin_mezclar_pagos(self):
        DocumentoTributario.objects.create(fecha_emision=date(2026, 8, 10), cliente=self.cliente, tipo_documento="FACTURA", numero="1", neto=100, iva=19, total=119)
        DocumentoCompra.objects.create(fecha_documento=date(2026, 8, 11), proveedor=self.proveedor, centro_costo=self.cc, tipo_documento="FACTURA", numero="1", neto=200, iva=38, total=238)
        calcular_iva_periodo(self.periodo)
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.iva_ventas, Decimal("19"))
        self.assertEqual(self.periodo.iva_compras, Decimal("38"))
        self.assertEqual(self.periodo.subtotal_iva, Decimal("-19"))
        self.assertEqual(self.periodo.detalles.count(), 2)

    def test_nota_credito_resta_y_anulado_se_excluye(self):
        DocumentoTributario.objects.create(fecha_emision=date(2026, 8, 10), cliente=self.cliente, tipo_documento="FACTURA", numero="2", neto=100, iva=19, total=119)
        DocumentoTributario.objects.create(fecha_emision=date(2026, 8, 11), cliente=self.cliente, tipo_documento="NOTA_CREDITO", numero="3", neto=20, iva=4, total=24)
        DocumentoCompra.objects.create(fecha_documento=date(2026, 8, 12), proveedor=self.proveedor, tipo_documento="FACTURA", numero="2", neto=50, iva=9.5, total=59.5, estado=DocumentoCompra.Estado.ANULADO)
        calcular_iva_periodo(self.periodo)
        self.periodo.refresh_from_db()
        self.assertEqual(self.periodo.iva_ventas, Decimal("15"))
        self.assertEqual(self.periodo.detalles.count(), 2)

    def test_detecta_inconsistencias(self):
        DocumentoTributario.objects.create(fecha_emision=date(2026, 8, 10), cliente=self.cliente, tipo_documento="FACTURA", numero="4", neto=100, iva=19, total=120)
        self.assertEqual(len(inconsistencias_iva(self.periodo)), 1)
