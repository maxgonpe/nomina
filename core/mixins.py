class AuditFormMixin:
    """Asigna creado_por / actualizado_por en Create/Update CBV."""

    def form_valid(self, form):
        user = self.request.user
        if user.is_authenticated:
            if not form.instance.pk:
                form.instance.creado_por = user
            form.instance.actualizado_por = user
        return super().form_valid(form)
