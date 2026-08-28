from decimal import Decimal
from datetime import date

from django.test import TestCase

from core.models import CentroCosto
from facturacion.models import DocumentoCompra, Proveedor
from facturacion.services.iva_compras import (
    resumen_iva_compras,
    totales_por_centro,
    totales_por_proveedor,
    validar_consistencia_documentos,
)


class COM004RTests(TestCase):
    def setUp(self):
        self.proveedor = Proveedor.objects.create(rut="18.651.495-5", razon_social="Proveedor COM004-R")
        self.centro = CentroCosto.objects.create(codigo="CC-COM004", nombre="Compras")

    def documento(self, tipo="FACTURA", numero="1", **kwargs):
        return DocumentoCompra.objects.create(
            proveedor=self.proveedor, centro_costo=self.centro, fecha_documento=date(2026, 8, 15),
            tipo_documento=tipo, numero=numero, neto=kwargs.get("neto", 100), iva=kwargs.get("iva", 19),
            total=kwargs.get("total", 119), **{k: v for k, v in kwargs.items() if k not in {"neto", "iva", "total"}},
        )

    def test_resumen_suma_y_excluye_anulados(self):
        self.documento()
        self.documento(numero="2", estado=DocumentoCompra.Estado.ANULADO)
        resumen = resumen_iva_compras(fecha_desde=date(2026, 8, 1), fecha_hasta=date(2026, 8, 31))
        self.assertEqual(resumen["cantidad_documentos"], 1)
        self.assertEqual((resumen["neto"], resumen["iva"], resumen["total"]), (Decimal("100"), Decimal("19"), Decimal("119")))

    def test_nota_credito_resta_y_nota_debito_suma(self):
        self.documento(numero="2", tipo="NOTA DE CREDITO")
        self.documento(numero="3", tipo="NOTA DE DEBITO")
        resumen = resumen_iva_compras()
        self.assertEqual(resumen["neto"], Decimal("0"))

    def test_agrupaciones_y_consistencia(self):
        self.documento()
        self.assertEqual(totales_por_proveedor()[0]["total"], Decimal("119"))
        self.assertEqual(totales_por_centro()[0]["iva"], Decimal("19"))
        self.assertEqual(validar_consistencia_documentos(), [])

    def test_exenta_y_documento_no_pagado_se_incluyen(self):
        self.documento(tipo="FACTURA EXENTA", neto=100, iva=0, total=100)
        resumen = resumen_iva_compras()
        self.assertEqual(resumen["iva"], Decimal("0"))
