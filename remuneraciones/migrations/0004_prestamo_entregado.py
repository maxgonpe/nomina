from django.db import migrations


def cargar_conceptos_nuevos(apps, schema_editor):
    from remuneraciones.catalogo import CONCEPTOS_INICIALES

    Concepto = apps.get_model("remuneraciones", "ConceptoRemuneracion")
    for item in CONCEPTOS_INICIALES:
        defaults = {
            "nombre": item["nombre"],
            "tipo": item["tipo"],
            "naturaleza_calculo": item["naturaleza_calculo"],
            "proporcional_dias": item["proporcional_dias"],
            "editable": item["editable"],
            "orden": item["orden"],
            "activo": True,
        }
        if item.get("descripcion"):
            defaults["descripcion"] = item["descripcion"]
        Concepto.objects.get_or_create(
            codigo=item["codigo"],
            defaults=defaults,
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("remuneraciones", "0003_catalogo_conceptos"),
    ]

    operations = [
        migrations.RunPython(cargar_conceptos_nuevos, noop),
    ]
