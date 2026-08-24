def desactivar_trabajador(trabajador, usuario=None):
    trabajador.activo = False
    if usuario is not None:
        trabajador.actualizado_por = usuario
    trabajador.save()
    return trabajador
