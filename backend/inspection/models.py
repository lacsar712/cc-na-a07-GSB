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
    """留存的对照单：两条实测在留存时刻的快照，差数由服务端写入。"""

    left = models.ForeignKey(
        Inspection,
        verbose_name="实测甲",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sheets_as_left",
    )
    right = models.ForeignKey(
        Inspection,
        verbose_name="实测乙",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sheets_as_right",
    )
    left_code = models.CharField("灯号甲", max_length=40)
    right_code = models.CharField("灯号乙", max_length=40)
    left_measured_cd = models.FloatField("留存时光强甲")
    right_measured_cd = models.FloatField("留存时光强乙")
    left_bearing_deg = models.FloatField("留存时偏角甲")
    right_bearing_deg = models.FloatField("留存时偏角乙")
    left_verdict = models.CharField("判词甲", max_length=20)
    right_verdict = models.CharField("判词乙", max_length=20)
    cd_diff = models.FloatField("亮度差")
    bearing_diff = models.FloatField("偏角差")
    created_by = models.CharField("留存人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def source_changed(self) -> bool:
        """留存后任一来源实测被改正（或删除）则为真。"""
        pairs = (
            (self.left, self.left_code, self.left_measured_cd, self.left_bearing_deg, self.left_verdict),
            (self.right, self.right_code, self.right_measured_cd, self.right_bearing_deg, self.right_verdict),
        )
        for inspection, code, measured, bearing, verdict in pairs:
            if inspection is None:
                return True
            if (
                inspection.aid_code != code
                or inspection.measured_cd != measured
                or inspection.bearing_error_deg != bearing
                or inspection.verdict != verdict
            ):
                return True
        return False
