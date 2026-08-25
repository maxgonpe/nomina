from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import CentroCosto
from rendiciones.models import DocumentoRendicion, Rendicion
from rendiciones.services.rendiciones import agregar_detalle
from rrhh.models import Trabajador

User = get_user_model()

PDF_BYTES = b"%PDF-1.4 minimal test file"
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
    b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
    b"\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


class DocumentoVistaTests(TestCase):
    def setUp(self):
        self._media = tempfile.TemporaryDirectory()
        self.settings_override = override_settings(
            MEDIA_ROOT=Path(self._media.name)
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self._media.cleanup)

        self.user = User.objects.create_user("ren4", password="clave-segura")
        perms = Permission.objects.filter(
            content_type__app_label="rendiciones",
            codename__in=[
                "view_rendicion",
                "change_rendicion",
                "add_documentorendicion",
                "delete_documentorendicion",
            ],
        )
        self.user.user_permissions.set(perms)
        self.client.force_login(self.user)
        self.trabajador = Trabajador.objects.create(
            rut="18.651.495-5",
            nombre_completo="Ana Pérez",
        )
        self.egc = CentroCosto.objects.create(codigo="EGC", nombre="EGC")
        self.rendicion = Rendicion.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 8, 12),
            descripcion="Materiales",
            total_declarado=Decimal("100000.00"),
        )

    def test_subir_pdf(self):
        response = self.client.post(
            reverse("rendiciones:documento_agregar", args=[self.rendicion.pk]),
            {
                "tipo": DocumentoRendicion.Tipo.BOLETA,
                "descripcion": "Boleta ferretería",
                "archivo": SimpleUploadedFile(
                    "boleta_001.pdf",
                    PDF_BYTES,
                    content_type="application/pdf",
                ),
            },
        )
        self.assertEqual(response.status_code, 302)
        doc = DocumentoRendicion.objects.get()
        self.assertEqual(doc.tipo, DocumentoRendicion.Tipo.BOLETA)
        self.assertIn("rendiciones/2026/", doc.archivo.name)
        self.assertIn(f"/{self.rendicion.pk}/", doc.archivo.name)
        self.assertTrue(doc.archivo.name.endswith(".pdf"))
        self.assertEqual(doc.creado_por, self.user)

    def test_subir_imagen(self):
        response = self.client.post(
            reverse("rendiciones:documento_agregar", args=[self.rendicion.pk]),
            {
                "tipo": DocumentoRendicion.Tipo.COMPROBANTE,
                "descripcion": "",
                "archivo": SimpleUploadedFile(
                    "foto.PNG",
                    PNG_BYTES,
                    content_type="image/png",
                ),
            },
        )
        self.assertEqual(response.status_code, 302)
        doc = DocumentoRendicion.objects.get()
        self.assertTrue(doc.archivo.name.lower().endswith(".png"))

    def test_rechaza_extension_no_permitida(self):
        response = self.client.post(
            reverse("rendiciones:documento_agregar", args=[self.rendicion.pk]),
            {
                "tipo": DocumentoRendicion.Tipo.OTRO,
                "descripcion": "",
                "archivo": SimpleUploadedFile(
                    "virus.exe",
                    b"MZ",
                    content_type="application/octet-stream",
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DocumentoRendicion.objects.count(), 0)
        self.assertContains(response, "PDF, JPG o PNG")

    def test_eliminar_en_borrador(self):
        doc = DocumentoRendicion.objects.create(
            rendicion=self.rendicion,
            tipo=DocumentoRendicion.Tipo.FACTURA,
            archivo=SimpleUploadedFile(
                "f.pdf", PDF_BYTES, content_type="application/pdf"
            ),
        )
        response = self.client.post(
            reverse("rendiciones:documento_eliminar", args=[doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DocumentoRendicion.objects.count(), 0)

    def test_bloquea_eliminacion_si_presentada(self):
        agregar_detalle(self.rendicion, centro_costo=self.egc, monto="100000")
        self.rendicion.estado = Rendicion.Estado.PRESENTADA
        self.rendicion.save(update_fields=["estado"])
        doc = DocumentoRendicion.objects.create(
            rendicion=self.rendicion,
            tipo=DocumentoRendicion.Tipo.BOLETA,
            archivo=SimpleUploadedFile(
                "b.pdf", PDF_BYTES, content_type="application/pdf"
            ),
        )
        response = self.client.post(
            reverse("rendiciones:documento_eliminar", args=[doc.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DocumentoRendicion.objects.count(), 1)

    def test_bloquea_alta_si_presentada(self):
        self.rendicion.estado = Rendicion.Estado.PRESENTADA
        self.rendicion.save(update_fields=["estado"])
        response = self.client.post(
            reverse("rendiciones:documento_agregar", args=[self.rendicion.pk]),
            {
                "tipo": DocumentoRendicion.Tipo.OTRO,
                "descripcion": "",
                "archivo": SimpleUploadedFile(
                    "x.pdf", PDF_BYTES, content_type="application/pdf"
                ),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DocumentoRendicion.objects.count(), 0)

    def test_ficha_lista_documentos(self):
        DocumentoRendicion.objects.create(
            rendicion=self.rendicion,
            tipo=DocumentoRendicion.Tipo.BOLETA,
            descripcion="Respaldo",
            archivo=SimpleUploadedFile(
                "r.pdf", PDF_BYTES, content_type="application/pdf"
            ),
        )
        response = self.client.get(
            reverse("rendiciones:rendicion_detalle", args=[self.rendicion.pk])
        )
        self.assertContains(response, "Documentos y respaldos")
        self.assertContains(response, "Boleta")
        self.assertContains(response, "Respaldo")
