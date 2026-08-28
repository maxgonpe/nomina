from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto, ParametroNegocio, ParametroValor
from facturacion.forms import CategoriaCompraForm, ClienteForm, CobroDocumentoForm, DocumentoCompraForm, DocumentoTributarioForm, ObraForm, PagoDocumentoCompraForm, ProveedorForm
from facturacion.models import CategoriaCompra, Cliente, CobroDocumentoTributario, DocumentoCompra, DocumentoTributario, Obra, PagoDocumentoCompra, Proveedor
from facturacion.services.documentos import calcular_documento, recalcular_documento
from facturacion.services.integracion import cobros_financieros, datos_impuestos, filas_excel
from facturacion.services.reportes import resumen_facturacion
from facturacion.services.reportes_compras import totales_por_categoria_compra


class ClienteTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="facturacion", password="clave-segura"
        )
        self.client.force_login(self.user)

    def test_crear_cliente_valido_normaliza_rut_y_razon_social(self):
        response = self.client.post(reverse("facturacion:cliente_crear"), {
            "rut": "18.651.495-5",
            "razon_social": "  Empresa   de   Prueba  ",
            "observaciones": "Cliente de prueba",
        })
        self.assertRedirects(response, reverse("facturacion:cliente_detalle", args=[1]))
        cliente = Cliente.objects.get()
        self.assertEqual(cliente.rut_normalizado, "186514955")
        self.assertEqual(cliente.razon_social, "Empresa de Prueba")
        self.assertTrue(cliente.activo)

    def test_rechaza_rut_invalido_y_duplicado(self):
        self.assertFalse(ClienteForm(data={
            "rut": "18.651.495-6", "razon_social": "Cliente"
        }).is_valid())
        Cliente.objects.create(rut="18.651.495-5", razon_social="Original")
        form = ClienteForm(data={
            "rut": "18651495-5", "razon_social": "Duplicado"
        })
        self.assertFalse(form.is_valid())
        self.assertIn("Ya existe", str(form.errors))

    def test_editar_y_desactivar_conserva_cliente(self):
        cliente = Cliente.objects.create(
            rut="16.287.425-K", razon_social="Cliente Original"
        )
        response = self.client.post(reverse("facturacion:cliente_editar", args=[cliente.pk]), {
            "rut": "16.287.425-K", "razon_social": "Cliente Editado", "activo": "on"
        })
        self.assertRedirects(response, reverse("facturacion:cliente_detalle", args=[cliente.pk]))
        response = self.client.post(reverse("facturacion:cliente_desactivar", args=[cliente.pk]))
        self.assertRedirects(response, reverse("facturacion:cliente_detalle", args=[cliente.pk]))
        cliente.refresh_from_db()
        self.assertFalse(cliente.activo)
        self.assertEqual(cliente.razon_social, "Cliente Editado")

    def test_listado_excluye_inactivos_por_defecto(self):
        Cliente.objects.create(rut="16.287.425-K", razon_social="Inactivo", activo=False)
        response = self.client.get(reverse("facturacion:cliente_lista"))
        self.assertNotContains(response, "Inactivo")
        response = self.client.get(reverse("facturacion:cliente_lista"), {"incluir_inactivos": "1"})
        self.assertContains(response, "Inactivo")


class ProveedorTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="proveedores", password="clave-segura")
        self.client.force_login(self.user)

    def test_crear_editar_y_desactivar_proveedor(self):
        response = self.client.post(reverse("facturacion:proveedor_crear"), {"rut": "18.651.495-5", "razon_social": "  Proveedor   de   Prueba  ", "observaciones": ""})
        proveedor = Proveedor.objects.get()
        self.assertRedirects(response, reverse("facturacion:proveedor_detalle", args=[proveedor.pk]))
        self.assertEqual(proveedor.razon_social, "Proveedor de Prueba")
        self.client.post(reverse("facturacion:proveedor_editar", args=[proveedor.pk]), {"rut": "18.651.495-5", "razon_social": "Proveedor Editado", "activo": "on"})
        self.client.post(reverse("facturacion:proveedor_desactivar", args=[proveedor.pk]))
        proveedor.refresh_from_db()
        self.assertFalse(proveedor.activo)

    def test_rechaza_rut_invalido_y_duplicado(self):
        self.assertFalse(ProveedorForm(data={"rut": "18.651.495-6", "razon_social": "Proveedor"}).is_valid())
        Proveedor.objects.create(rut="18.651.495-5", razon_social="Original")
        self.assertFalse(ProveedorForm(data={"rut": "18651495-5", "razon_social": "Duplicado"}).is_valid())

    def test_listado_oculta_inactivos_por_defecto(self):
        Proveedor.objects.create(rut="18.651.495-5", razon_social="Proveedor Inactivo", activo=False)
        response = self.client.get(reverse("facturacion:proveedor_lista"))
        self.assertNotContains(response, "Proveedor Inactivo")


class DocumentoCompraTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="compras", password="clave-segura")
        self.client.force_login(self.user)
        self.proveedor = Proveedor.objects.create(rut="18.651.495-5", razon_social="Proveedor Compra")
        parametro = ParametroNegocio.objects.create(codigo="TASA_IVA", nombre="Tasa IVA")
        ParametroValor.objects.create(parametro=parametro, valor="0.19", vigencia_desde="2026-01-01")

    def test_alta_sin_categoria_queda_sin_clasificar(self):
        form = DocumentoCompraForm(data={"fecha_documento": "2026-08-15", "proveedor": self.proveedor.pk, "tipo_documento": "FACTURA", "numero": "SIN-1", "neto": "100"})
        self.assertTrue(form.is_valid(), form.errors)
        compra = form.save()
        self.assertEqual(compra.categoria_compra.codigo, "SIN_CLASIFICAR")

    def test_clasificacion_agrupa_independiente_del_proveedor(self):
        materiales = CategoriaCompra.objects.get(codigo="MAT_MATERIALES")
        combustible = CategoriaCompra.objects.get(codigo="GAS_COMBUSTIBLE")
        otro = Proveedor.objects.create(rut="16.287.425-K", razon_social="Otro proveedor")
        DocumentoCompra.objects.create(proveedor=self.proveedor, categoria_compra=materiales, fecha_documento="2026-08-01", tipo_documento="FACTURA", numero="MAT-1", neto=100, iva=19, total=119)
        DocumentoCompra.objects.create(proveedor=otro, categoria_compra=materiales, fecha_documento="2026-08-02", tipo_documento="FACTURA", numero="MAT-2", neto=200, iva=38, total=238)
        DocumentoCompra.objects.create(proveedor=self.proveedor, categoria_compra=combustible, fecha_documento="2026-08-03", tipo_documento="FACTURA", numero="GAS-1", neto=50, iva=9.5, total=59.5)
        grupos = {fila["categoria_compra"].codigo: fila["neto"] for fila in totales_por_categoria_compra()}
        self.assertEqual(grupos["MAT_MATERIALES"], Decimal("300"))
        self.assertEqual(grupos["GAS_COMBUSTIBLE"], Decimal("50"))

    def test_categoria_inactiva_no_se_ofrece_en_nuevas_compras(self):
        categoria = CategoriaCompra.objects.get(codigo="MAT_MATERIALES")
        categoria.activa = False
        categoria.save()
        form = DocumentoCompraForm()
        self.assertNotIn(categoria, form.fields["categoria_compra"].queryset)

    def test_crea_compra_calcula_importes_y_anula(self):
        response = self.client.post(reverse("facturacion:compra_crear"), {"fecha_documento": "2026-08-15", "proveedor": self.proveedor.pk, "tipo_documento": "FACTURA", "numero": "4532", "neto": "1000000", "observaciones": ""})
        compra = DocumentoCompra.objects.get()
        self.assertRedirects(response, reverse("facturacion:compra_detalle", args=[compra.pk]))
        self.assertEqual(compra.iva, Decimal("190000.00"))
        self.assertEqual(compra.total, Decimal("1190000.00"))
        self.client.post(reverse("facturacion:compra_anular", args=[compra.pk]), {"motivo_anulacion": "Compra registrada por error"})
        compra.refresh_from_db()
        self.assertEqual(compra.estado, DocumentoCompra.Estado.ANULADO)

    def test_rechaza_duplicado_y_neto_negativo(self):
        DocumentoCompra.objects.create(proveedor=self.proveedor, fecha_documento="2026-08-01", tipo_documento="FACTURA", numero="1", neto=1, iva=0, total=1)
        form = DocumentoCompraForm(data={"fecha_documento": "2026-08-02", "proveedor": self.proveedor.pk, "tipo_documento": "FACTURA", "numero": "1", "neto": "2"})
        self.assertFalse(form.is_valid())
        self.assertFalse(DocumentoCompraForm(data={"fecha_documento": "2026-08-02", "proveedor": self.proveedor.pk, "tipo_documento": "FACTURA", "numero": "2", "neto": "-1"}).is_valid())

    def test_pagos_derivan_estado_y_anulacion_recalcula_saldo(self):
        compra = DocumentoCompra.objects.create(proveedor=self.proveedor, fecha_documento="2026-08-01", tipo_documento="FACTURA", numero="20", neto=100, iva=19, total=119)
        self.client.post(reverse("facturacion:pago_compra_crear", args=[compra.pk]), {"fecha": "2026-08-20", "monto": "50", "medio_pago": "Transferencia"})
        compra.refresh_from_db()
        self.assertEqual(compra.estado, DocumentoCompra.Estado.PARCIAL)
        pago = PagoDocumentoCompra.objects.get()
        self.assertFalse(PagoDocumentoCompraForm(data={"fecha": "2026-08-21", "monto": "70"}, documento=compra).is_valid())
        self.client.post(reverse("facturacion:pago_compra_anular", args=[pago.pk]), {"motivo_anulacion": "Error de digitación"})
        compra.refresh_from_db()
        self.assertEqual(compra.total_pagado, Decimal("0.00"))
        self.assertEqual(compra.estado, DocumentoCompra.Estado.REGISTRADO)


class ObraTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="obras", password="clave-segura")
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(rut="18.651.495-5", razon_social="Cliente Obra")
        self.otro_cliente = Cliente.objects.create(rut="16.287.425-K", razon_social="Otro Cliente")
        self.centro = CentroCosto.objects.create(codigo="OBRA", nombre="Centro obra")

    def test_crear_obra_desde_cliente_y_listar_por_cliente(self):
        response = self.client.post(reverse("facturacion:cliente_obra_crear", args=[self.cliente.pk]), {
            "codigo": " obra-01 ", "nombre": " Instalación EGC ", "cliente": self.cliente.pk,
            "centro_costo": self.centro.pk, "fecha_inicio": "2026-01-01", "fecha_termino": "2026-12-31",
            "estado": Obra.Estado.ACTIVA, "observaciones": ""
        })
        obra = Obra.objects.get()
        self.assertRedirects(response, reverse("facturacion:obra_detalle", args=[obra.pk]))
        self.assertEqual(obra.codigo, "OBRA-01")
        self.assertEqual(obra.nombre, "Instalación EGC")
        response = self.client.get(reverse("facturacion:cliente_obras", args=[self.cliente.pk]))
        self.assertContains(response, "OBRA-01")
        self.assertNotContains(response, "Otra obra")

    def test_valida_codigo_cliente_y_fechas(self):
        obra = Obra.objects.create(codigo="OBRA-01", nombre="Original", cliente=self.cliente)
        self.assertFalse(ObraForm(data={"codigo": "OBRA-01", "nombre": "Otra", "cliente": self.otro_cliente.pk}).is_valid())
        form = ObraForm(data={"codigo": "OBRA-02", "nombre": "Otra", "cliente": self.cliente.pk, "fecha_inicio": "2026-12-31", "fecha_termino": "2026-01-01"})
        self.assertFalse(form.is_valid())
        self.assertIn("fecha_termino", form.errors)

    def test_obra_terminada_se_conserva(self):
        obra = Obra.objects.create(codigo="OBRA-TERMINADA", nombre="Terminada", cliente=self.cliente, estado=Obra.Estado.TERMINADA)
        self.assertTrue(Obra.objects.filter(pk=obra.pk, estado=Obra.Estado.TERMINADA).exists())


class DocumentoTributarioTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(username="documentos", password="clave-segura")
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(rut="18.651.495-5", razon_social="Cliente Documento")
        self.otro_cliente = Cliente.objects.create(rut="16.287.425-K", razon_social="Otro Cliente")
        self.obra = Obra.objects.create(codigo="OBRA-DOC", nombre="Obra documento", cliente=self.cliente)
        parametro = ParametroNegocio.objects.create(codigo="TASA_IVA", nombre="Tasa IVA")
        ParametroValor.objects.create(parametro=parametro, valor="0.19", vigencia_desde="2026-01-01")

    def datos(self, **extra):
        data = {"fecha_emision": "2026-08-15", "cliente": self.cliente.pk, "obra": self.obra.pk,
                "tipo_documento": "FACTURA", "numero": "1254", "neto": "1000000", "observaciones": ""}
        data.update(extra)
        return data

    def test_crea_factura_y_calcula_iva_total(self):
        response = self.client.post(reverse("facturacion:documento_crear"), self.datos())
        documento = DocumentoTributario.objects.get()
        self.assertRedirects(response, reverse("facturacion:documento_detalle", args=[documento.pk]))
        self.assertEqual(documento.iva, Decimal("190000.00"))
        self.assertEqual(documento.total, Decimal("1190000.00"))

    def test_cambio_de_tasa_no_modifica_snapshot_y_falta_tasa_falla(self):
        calculado = calcular_documento("2026-08-15", "FACTURA", Decimal("100"))
        self.assertEqual(calculado["tasa_iva_snapshot"], Decimal("0.19"))
        ParametroValor.objects.create(parametro_id=1, valor="0.20", vigencia_desde="2027-01-01")
        self.assertEqual(calcular_documento("2026-08-15", "FACTURA", Decimal("100"))["iva"], Decimal("19.00"))

    def test_documento_pagado_no_se_puede_recalcular(self):
        documento = DocumentoTributario.objects.create(fecha_emision="2026-08-15", cliente=self.cliente, tipo_documento="FACTURA", numero="PAGADO", neto=100, estado="PAGADA", iva=19, total=119, tasa_iva_snapshot="0.19")
        with self.assertRaises(ValidationError):
            recalcular_documento(documento)

    def test_rechaza_obra_de_otro_cliente_y_duplicado(self):
        form = DocumentoTributarioForm(data=self.datos(obra=Obra.objects.create(codigo="OTRA", nombre="Otra", cliente=self.otro_cliente).pk))
        self.assertFalse(form.is_valid())
        self.client.post(reverse("facturacion:documento_crear"), self.datos())
        form = DocumentoTributarioForm(data=self.datos())
        self.assertFalse(form.is_valid())
        self.assertIn("Ya existe", str(form.errors))

    def test_documento_exento_no_calcula_iva_y_se_anula(self):
        response = self.client.post(reverse("facturacion:documento_crear"), self.datos(tipo_documento="FACTURA_EXENTA", numero="9"))
        documento = DocumentoTributario.objects.get()
        self.assertRedirects(response, reverse("facturacion:documento_detalle", args=[documento.pk]))
        documento.refresh_from_db()
        self.assertEqual(documento.iva, Decimal("0.00"))
        self.client.post(reverse("facturacion:documento_anular", args=[documento.pk]), {"motivo": "Documento emitido por error"})
        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoTributario.Estado.ANULADA)

    def test_cobros_derivan_estado_y_rechazan_sobrepago(self):
        self.client.post(reverse("facturacion:documento_crear"), self.datos())
        documento = DocumentoTributario.objects.get()
        self.client.post(reverse("facturacion:cobro_crear", args=[documento.pk]), {"fecha": "2026-08-20", "monto": "500000", "medio_pago": "Transferencia"})
        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoTributario.Estado.PARCIAL)
        form = CobroDocumentoForm(data={"fecha": "2026-08-21", "monto": "700000"}, documento=documento)
        self.assertFalse(form.is_valid())
        self.assertIn("saldo", str(form.errors).lower())
        self.client.post(reverse("facturacion:cobro_crear", args=[documento.pk]), {"fecha": "2026-08-22", "monto": "690000"})
        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoTributario.Estado.PAGADA)
        self.assertEqual(documento.saldo_pendiente, Decimal("0.00"))

    def test_anulado_no_admite_cobro(self):
        documento = DocumentoTributario.objects.create(fecha_emision="2026-08-15", cliente=self.cliente, tipo_documento="FACTURA", numero="ANULADO", neto=100, iva=19, total=119, tasa_iva_snapshot="0.19", estado="ANULADA")
        form = CobroDocumentoForm(data={"fecha": "2026-08-20", "monto": "10"}, documento=documento)
        self.assertFalse(form.is_valid())

    def test_integraciones_separan_emision_cobro_y_excluyen_anulados(self):
        self.client.post(reverse("facturacion:documento_crear"), self.datos())
        documento = DocumentoTributario.objects.get()
        CobroDocumentoTributario.objects.create(documento=documento, fecha="2026-09-05", monto="1190000")
        documento.refresh_from_db()
        impuestos = datos_impuestos(documento)
        self.assertEqual(impuestos["fecha_emision"].month, 8)
        self.assertEqual(len(cobros_financieros(2026, 9)), 1)
        self.assertEqual(cobros_financieros(2026, 9)[0]["fecha"].month, 9)
        self.assertEqual(filas_excel([documento])[0]["item"], 1)
        documento.estado = DocumentoTributario.Estado.ANULADA
        documento.save(update_fields=["estado"])
        self.assertIsNone(datos_impuestos(documento))
        self.assertEqual(filas_excel(), [])

    def test_resumen_excluye_anulados_y_calcula_totales(self):
        self.client.post(reverse("facturacion:documento_crear"), self.datos())
        documento = DocumentoTributario.objects.get()
        CobroDocumentoTributario.objects.create(documento=documento, fecha="2026-08-20", monto="500000")
        documento.estado = DocumentoTributario.Estado.PARCIAL
        documento.save(update_fields=["estado"])
        resumen = resumen_facturacion({"anio": 2026, "mes": 8})
        self.assertEqual(resumen["neto"], Decimal("1000000.00"))
        self.assertEqual(resumen["iva"], Decimal("190000.00"))
        self.assertEqual(resumen["cobrado"], Decimal("500000.00"))
        self.assertEqual(resumen["saldo"], Decimal("690000.00"))
