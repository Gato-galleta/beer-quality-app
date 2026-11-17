from django.conf import settings
from django.db import models


class LotAnalysis(models.Model):
    """Registro de cada analisis de lote: entrada, resultado y quien lo ejecuto.

    Sirve de historial para el analisis de tendencias y de trazabilidad (auditoria).
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    lot_code = models.CharField("lote", max_length=60, blank=True)
    brand = models.CharField("marca", max_length=60, blank=True)
    package_format = models.CharField("formato", max_length=20, blank=True)
    measurements = models.JSONField("mediciones")
    result = models.JSONField("resultado")
    decision = models.CharField(max_length=20)

    # Decision final del especialista (una sola vez; no se modifica despues)
    final_decision = models.CharField("decisión del especialista", max_length=20, blank=True)
    final_comment = models.TextField("comentario del especialista", blank=True)
    final_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
        verbose_name="confirmado por",
    )
    final_at = models.DateTimeField("confirmado el", null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "análisis de lote"
        verbose_name_plural = "análisis de lotes"
        permissions = [("confirm_lotanalysis", "Puede confirmar la decisión final de un lote")]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.lot_code or 'sin lote'} {self.decision}"
