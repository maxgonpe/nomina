from django.db import migrations


def cargar_conceptos(apps, schema_editor):
    from remuneraciones.catalogo import CONCEPTOS_INICIALES

    Concepto = apps.get_model("remuneraciones", "ConceptoRemuneracion")
    for item in CONCEPTOS_INICIALES:
        Concepto.objects.get_or_create(
            codigo=item["codigo"],
            defaults={
                "nombre": item["nombre"],
                "tipo": item["tipo"],
                "naturaleza_calculo": item["naturaleza_calculo"],
                "proporcional_dias": item["proporcional_dias"],
                "editable": item["editable"],
                "orden": item["orden"],
                "activo": True,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        (
            "remuneraciones",
            "0002_alter_periodoremuneracion_options_and_more",
        ),
    ]

    operations = [
        migrations.RunPython(cargar_conceptos, noop),
    ]
