from django.db import models

class FetchLog(models.Model):
    subject = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, default="")
    industry = models.CharField(max_length=200, blank=True, default="")
    days = models.IntegerField(default=7)
    limit = models.IntegerField(default=10)
    result_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # Free-form params if you want to store request extras
    search_params = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def _str_(self):
        return f"{self.subject} ({self.created_at:%Y-%m-%d %H:%M:%S})"