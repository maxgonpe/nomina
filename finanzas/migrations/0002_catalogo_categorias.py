from django.db import migrations, models

def crear_catalogo(apps, schema_editor):
    Categoria = apps.get_model("finanzas", "CategoriaFinanciera")
    datos = [("ING_CLIENTES", "Cobros de clientes", "INGRESO", False), ("EGR_REMUNERACIONES", "Remuneraciones", "EGRESO", False), ("EGR_PROVEEDORES", "Proveedores", "EGRESO", False), ("EGR_RENDICIONES", "Rendiciones", "EGRESO", False), ("EGR_IMPUESTOS", "Impuestos", "EGRESO", False), ("EGR_BANCARIOS", "Gastos bancarios", "EGRESO", True), ("ING_OTROS", "Otros ingresos", "INGRESO", True), ("EGR_OTROS", "Otros egresos", "EGRESO", True)]
    for codigo, nombre, tipo, manual in datos:
        Categoria.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "tipo": tipo, "permite_manual": manual})

class Migration(migrations.Migration):
    dependencies = [("finanzas", "0001_initial")]
    operations = [migrations.AddField(model_name="categoriafinanciera", name="permite_manual", field=models.BooleanField(default=False)), migrations.RunPython(crear_catalogo, migrations.RunPython.noop)]
