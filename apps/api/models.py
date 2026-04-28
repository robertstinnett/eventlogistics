from django.db import models


# API app is serializer/view focused; model file is intentionally minimal.
class ApiPlaceholder(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
