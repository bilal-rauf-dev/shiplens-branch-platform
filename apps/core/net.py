"""Resolve the client address consistently behind the configured trusted proxies."""

from ipaddress import ip_address

from django.conf import settings


def client_ip(request):
    """Use the proxy-appended address, never an arbitrary leftmost forwarded entry."""
    hops = settings.TRUSTED_PROXY_HOPS
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")
    if hops > 0 and len(forwarded) >= hops:
        try:
            return str(ip_address(forwarded[-hops].strip()))
        except ValueError:
            pass
    try:
        return str(ip_address((request.META.get("REMOTE_ADDR") or "").strip()))
    except ValueError:
        return None


def client_ip_key(group, request):
    """Adapt the same address resolver to django-ratelimit's key signature."""
    return client_ip(request) or ""
