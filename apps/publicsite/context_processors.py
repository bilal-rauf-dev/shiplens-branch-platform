from apps.core.routes import PUBLIC_ROUTES


def public_context(request):
    match = request.resolver_match
    return {"public_page": bool(match and match.url_name in PUBLIC_ROUTES)}
