from django.db import models


class AuditLog(models.Model):
    instance = models.ForeignKey(
        "instance.Instance",
        db_column="INSTANCE_ID",
        null=True,
        on_delete=models.CASCADE,
    )
    url = models.TextField(db_column="URL")
    method = models.CharField(db_column="METHOD", max_length=20)
    description = models.TextField(db_column="DESCRIPTION")
    system_info = models.JSONField(db_column="SYSTEM_INFO")
    user = models.ForeignKey("user.User", db_column="USER_ID", on_delete=models.CASCADE)
    timestamp = models.DateTimeField(db_column="TIMESTAMP", auto_now_add=True)

    class Meta:
        managed = True
        db_table = "AUDIT_LOG"
