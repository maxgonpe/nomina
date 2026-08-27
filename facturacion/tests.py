from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import CentroCosto, ParametroNegocio, ParametroValor
from facturacion.forms import ClienteForm, DocumentoTributarioForm, ObraForm
from facturacion.models import Cliente, DocumentoTributario, Obra


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
        parametro = ParametroNegocio.objects.create(codigo="IVA", nombre="IVA")
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
        self.client.post(reverse("facturacion:documento_anular", args=[documento.pk]), {"confirmacion": "on"})
        documento.refresh_from_db()
        self.assertEqual(documento.estado, DocumentoTributario.Estado.ANULADA)
