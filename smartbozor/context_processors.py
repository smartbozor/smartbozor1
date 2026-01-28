from apps.rent.models import Thing


def smartbozor(request):
    if not request.user.is_authenticated:
        return {}

    current_title = ""
    cls = request.resolver_match.func
    if cls and hasattr(cls, "view_class"):
        cls = cls.view_class
        if cls and hasattr(cls, "TITLE"):
            current_title = cls.TITLE

    allowed_bazaar = list(request.user.allowed_bazaar.prefetch_related('district__region').order_by("id").all())
    return {
        "ALLOWED_BAZAAR": allowed_bazaar,
        "ALLOWED_BAZAAR_ID": set([row.id for row in allowed_bazaar]),
        "TITLE": current_title,
        "THINGS": Thing.objects.order_by('id').all()
    }
