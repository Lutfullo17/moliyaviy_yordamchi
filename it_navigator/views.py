from django.http import JsonResponse


def health_check(request):
    return JsonResponse(
        {
            "message": "IT Navigator backend ishlayapti",
            "status": "ok",
        }
    )
