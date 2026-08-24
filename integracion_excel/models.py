# Esta app será la responsable de que podamos conservar el diseño de los #libros actuales.

from django.db import models

from core.models import AuditModel


class PlantillaExcel(AuditModel):

    class Tipo(models.TextChoices):
        NOMINA = (
            "NOMINA",
            "Nómina de remuneraciones",
        )
        PAGOS_GENERALES = (
            "PAGOS_GENERALES",
            "Planilla de pagos generales",
        )
        OTRO = "OTRO", "Otro"

    codigo = models.CharField(
        max_length=50,
        unique=True,
    )

    nombre = models.CharField(
        max_length=150,
    )

    tipo = models.CharField(
        max_length=30,
        choices=Tipo.choices,
    )

    archivo = models.FileField(
        upload_to="excel/plantillas/",
    )

    version = models.CharField(
        max_length=30,
        default="1",
    )

    activo = models.BooleanField(
        default=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["codigo"]

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.codigo} - "
            f"{self.nombre}"
        )


class MapeoExcel(AuditModel):

    class TipoMapeo(models.TextChoices):
        CELDA = "CELDA", "Celda"
        RANGO = "RANGO", "Rango"
        TABLA = "TABLA", "Tabla"
        COLUMNA = "COLUMNA", "Columna"
        GRAFICO = "GRAFICO", "Gráfico"

    plantilla = models.ForeignKey(
        PlantillaExcel,
        on_delete=models.CASCADE,
        related_name="mapeos",
    )

    codigo = models.CharField(
        max_length=100,
    )

    hoja = models.CharField(
        max_length=100,
    )

    tipo_mapeo = models.CharField(
        max_length=15,
        choices=TipoMapeo.choices,
    )

    referencia_excel = models.CharField(
        max_length=150,
    )

    origen = models.CharField(
        max_length=250,
        help_text=(
            "Clave lógica de origen. Ejemplo: "
            "remuneraciones.total_mes"
        ),
    )

    formato_excel = models.CharField(
        max_length=100,
        blank=True,
    )

    activo = models.BooleanField(
        default=True,
    )

    observaciones = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "plantilla",
            "hoja",
            "codigo",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "plantilla",
                    "codigo",
                ],
                name="uq_mapeo_excel_codigo",
            ),
        ]

    def __str__(self):
        return (
            f"{self.plantilla.codigo} - "
            f"{self.codigo}"
        )


class ImportacionExcel(AuditModel):

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PROCESANDO = "PROCESANDO", "Procesando"
        COMPLETADA = "COMPLETADA", "Completada"
        COMPLETADA_CON_ERRORES = (
            "COMPLETADA_CON_ERRORES",
            "Completada con errores",
        )
        ERROR = "ERROR", "Error"

    plantilla = models.ForeignKey(
        PlantillaExcel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="importaciones",
    )

    archivo_original = models.FileField(
        upload_to="excel/importaciones/%Y/%m/",
    )

    nombre_original = models.CharField(
        max_length=255,
        blank=True,
    )

    hash_archivo = models.CharField(
        max_length=128,
        blank=True,
        db_index=True,
    )

    estado = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    iniciado_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    finalizado_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    resumen = models.JSONField(
        default=dict,
        blank=True,
    )

    error = models.TextField(
        blank=True,
    )

    def __str__(self):
        return (
            f"Importación #{self.pk} - "
            f"{self.estado}"
        )


class ImportacionFila(AuditModel):

    class Estado(models.TextChoices):
        IMPORTADA = "IMPORTADA", "Importada"
        OMITIDA = "OMITIDA", "Omitida"
        ERROR = "ERROR", "Error"

    importacion = models.ForeignKey(
        ImportacionExcel,
        on_delete=models.CASCADE,
        related_name="filas",
    )

    hoja = models.CharField(
        max_length=100,
    )

    fila = models.PositiveIntegerField()

    modelo_destino = models.CharField(
        max_length=100,
        blank=True,
    )

    objeto_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
    )

    datos_originales = models.JSONField(
        default=dict,
        blank=True,
    )

    mensaje = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = [
            "importacion",
            "hoja",
            "fila",
        ]

    def __str__(self):
        return (
            f"{self.hoja}:{self.fila} "
            f"- {self.estado}"
        )


class ExportacionExcel(AuditModel):

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PROCESANDO = "PROCESANDO", "Procesando"
        COMPLETADA = "COMPLETADA", "Completada"
        ERROR = "ERROR", "Error"

    plantilla = models.ForeignKey(
        PlantillaExcel,
        on_delete=models.PROTECT,
        related_name="exportaciones",
    )

    anio = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    mes = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    archivo_generado = models.FileField(
        upload_to="excel/exportaciones/%Y/%m/",
        null=True,
        blank=True,
    )

    iniciado_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    finalizado_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    resumen = models.JSONField(
        default=dict,
        blank=True,
    )

    error = models.TextField(
        blank=True,
    )

    def __str__(self):
        return (
            f"Exportación #{self.pk} - "
            f"{self.plantilla.codigo}"
        )