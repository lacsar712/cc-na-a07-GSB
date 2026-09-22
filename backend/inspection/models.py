from django.db import models


class Inspection(models.Model):
    aid_code = models.CharField("航标编号", max_length=40)
    measured_cd = models.FloatField("实测光强")
    required_cd = models.FloatField("要求光强")
    bearing_error_deg = models.FloatField("方位偏差")
    verdict = models.CharField("结论", max_length=20)
    note = models.CharField("说明", max_length=200)
    created_by = models.CharField("登记人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class ComparisonSheet(models.Model):
    """两条实测留存的对照单。

    亮度差、偏角差在留存时由服务端算好写入存档，页面只读存档值，
    不随来源实测后来的改动而变化；快照字段用于识别来源是否已变动。
    """

    first = models.ForeignKey(
        Inspection,
        verbose_name="实测一",
        related_name="sheets_first",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    second = models.ForeignKey(
        Inspection,
        verbose_name="实测二",
        related_name="sheets_second",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    first_code = models.CharField("灯号一", max_length=40)
    second_code = models.CharField("灯号二", max_length=40)
    first_verdict = models.CharField("判词一", max_length=20)
    second_verdict = models.CharField("判词二", max_length=20)
    first_measured_cd = models.FloatField("实测一光强")
    second_measured_cd = models.FloatField("实测二光强")
    first_required_cd = models.FloatField("实测一要求光强")
    second_required_cd = models.FloatField("实测二要求光强")
    first_bearing_error_deg = models.FloatField("实测一方位偏差")
    second_bearing_error_deg = models.FloatField("实测二方位偏差")
    brightness_diff = models.FloatField("亮度差")
    bearing_diff = models.FloatField("偏角差")
    created_by = models.CharField("留存人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def _side_changed(self, prefix: str) -> bool:
        source = getattr(self, prefix)
        if source is None:
            return True
        return (
            source.aid_code != getattr(self, f"{prefix}_code")
            or source.measured_cd != getattr(self, f"{prefix}_measured_cd")
            or source.required_cd != getattr(self, f"{prefix}_required_cd")
            or source.bearing_error_deg != getattr(self, f"{prefix}_bearing_error_deg")
            or source.verdict != getattr(self, f"{prefix}_verdict")
        )

    @property
    def first_changed(self) -> bool:
        return self._side_changed("first")

    @property
    def second_changed(self) -> bool:
        return self._side_changed("second")

    @property
    def source_changed(self) -> bool:
        return self.first_changed or self.second_changed
