from django.db import migrations


def cargar_conceptos_costo(apps, schema_editor):
    from remuneraciones.catalogo import CONCEPTOS_COSTO_INICIALES

    Concepto = apps.get_model("remuneraciones", "ConceptoCostoTrabajador")
    for item in CONCEPTOS_COSTO_INICIALES:
        Concepto.objects.update_or_create(
            codigo=item["codigo"],
            defaults={
                "nombre": item["nombre"],
                "codigo_origen": item.get("codigo_origen") or "",
                "incluye_en_total": item.get("incluye_en_total", True),
                "orden": item["orden"],
                "descripcion": item.get("descripcion") or "",
                "activo": True,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("remuneraciones", "0006_conceptos_costo_catalogo"),
    ]

    operations = [
        migrations.RunPython(cargar_conceptos_costo, noop),
    ]
