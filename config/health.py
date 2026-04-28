from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse


def liveness(request):
    return JsonResponse({"status": "ok"})


def readiness(request):
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
    except OperationalError:
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)

    return JsonResponse({"status": "ok", "database": "available"})
