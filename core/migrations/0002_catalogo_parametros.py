from django.db import migrations


def cargar_parametros(apps, schema_editor):
    from core.catalogo import PARAMETROS_INICIALES, VALORES_INICIALES

    ParametroNegocio = apps.get_model("core", "ParametroNegocio")
    ParametroValor = apps.get_model("core", "ParametroValor")
    for item in PARAMETROS_INICIALES:
        ParametroNegocio.objects.get_or_create(
            codigo=item["codigo"],
            defaults={
                "nombre": item["nombre"],
                "descripcion": item["descripcion"],
                "activo": True,
            },
        )
    for item in VALORES_INICIALES:
        parametro = ParametroNegocio.objects.get(codigo=item["codigo"])
        ParametroValor.objects.get_or_create(
            parametro=parametro,
            vigencia_desde=item["vigencia_desde"],
            defaults={
                "valor": item["valor"],
                "vigencia_hasta": item["vigencia_hasta"],
                "observaciones": item["observaciones"],
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(cargar_parametros, noop),
    ]
