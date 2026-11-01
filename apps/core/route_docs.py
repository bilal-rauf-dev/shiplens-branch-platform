"""Render the URL resolver and permission registry as a reviewable route table."""

import ast
import inspect
import textwrap

from django.conf import settings
from django.urls import URLPattern, get_resolver
from django.utils.translation import override

from apps.accounts.permissions import OWN_ACTIONS, PERMISSIONS
from apps.core.routes import PUBLIC_ROUTES, ROUTE_ACTIONS


def view_methods(callback):
    """Read CBV handlers or the function's standard Django method decorator."""
    view_class = getattr(callback, "view_class", None)
    if view_class is not None:
        methods = []
        for method in view_class.http_method_names:
            handled = hasattr(view_class, method)
            # View.setup installs head = get when no separate head handler exists.
            if method == "head" and hasattr(view_class, "get"):
                handled = True
            if handled:
                methods.append(method.upper())
        return ", ".join(methods)

    function = inspect.unwrap(callback)
    source = ast.parse(textwrap.dedent(inspect.getsource(function)))
    for decorator in source.body[0].decorator_list:
        name = ast.unparse(decorator)
        if name == "require_GET":
            return "GET"
        if name == "require_POST":
            return "POST"
        if name == "require_safe":
            return "GET, HEAD"
        if isinstance(decorator, ast.Call) and name.startswith("require_http_methods("):
            return ", ".join(ast.literal_eval(decorator.args[0]))
    # Django's sitemap view has no method decorator or method dispatch guard.
    if function.__module__ == "django.contrib.sitemaps.views":
        return "Any (no view method restriction)"
    raise ValueError(f"Declare HTTP methods for function view {function.__qualname__}")


def resolved_routes(resolver, prefix="", namespaces=()):
    """Keep included prefixes and namespaces, just as request resolution does."""
    for pattern in resolver.url_patterns:
        path = prefix + str(pattern.pattern)
        if isinstance(pattern, URLPattern):
            name = ":".join((*namespaces, pattern.name or ""))
            yield "/" + path, name, pattern.callback
        else:
            children = (
                (*namespaces, pattern.namespace) if pattern.namespace else namespaces
            )
            yield from resolved_routes(pattern, path, children)


def render_routes():
    """Return deterministic Markdown, expanding every configured language prefix."""
    lines = [
        "# Route reference",
        "",
        "Generated — do not edit by hand. Run `python manage.py export_routes`.",
        "Sources: Django URL resolver, `apps/core/routes.py` and",
        "`apps/accounts/permissions.py`. See [permissions](permissions.md) for",
        "the action matrix and [architecture](architecture.md) for request flow.",
        "",
        "Paths show typed resolver parameters, for example `<int:pk>`; these are",
        "database IDs, not sample labels such as R9. Both configured locales are",
        "expanded. Static assets are served by WhiteNoise, outside this resolver.",
        "",
        "Methods describe view dispatch after middleware checks. Class views include",
        "inherited handlers (including PUT on Django FormView), automatic HEAD when",
        "enabled, and OPTIONS when enabled. Function require_GET accepts GET only.",
        "The framework sitemap has no view method restriction; CSRF still applies",
        "to unsafe requests. Public means no route-registry role check; it does not",
        "bypass CSRF, form validation or state rules. Public entries have no mapped",
        "permission action. Login redirects already signed-in users; language",
        "switching changes only the caller's preference.",
        "",
        "GLOBAL means a role grant across branches; ASSIGNED means current assigned",
        "branches only; OWN means the caller's account. Object lookups still apply",
        "scope. Anonymous private requests redirect to login (302); disallowed roles",
        "and CSRF failures get 403; missing/out-of-scope objects get 404. Pages and",
        "downloads normally return 200, successful forms normally redirect (302),",
        "invalid forms can return 200 or 400, state conflicts 409, limits 429 and",
        "unsupported restricted methods 405. These are shared conventions, not a",
        "promise of every status for every route. [Health OpenAPI](openapi.yaml)",
        "describes the only machine endpoint. [Exports](exports.md) describes files.",
        "",
        "| Path / parameters | Name | HTTP methods | Permission action | "
        "Roles and scope | Public |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    entries = {}
    for language, _label in settings.LANGUAGES:
        with override(language):
            for path, name, callback in resolved_routes(get_resolver()):
                if name not in PUBLIC_ROUTES and name not in ROUTE_ACTIONS:
                    raise ValueError(f"Unregistered route: {path} ({name})")
                public = name in PUBLIC_ROUTES
                action = ROUTE_ACTIONS.get(name)
                if public:
                    grants = "Anonymous and all staff roles (public route)"
                else:
                    grants = "; ".join(
                        f"{role}: {'OWN' if action in OWN_ACTIONS else scope}"
                        for role, scope in PERMISSIONS[action].items()
                    )
                methods = view_methods(callback)
                entries[(path, name)] = (
                    f"| `{path}` | `{name}` | {methods} | "
                    f"{f'`{action}`' if action else '—'} | {grants} | "
                    f"{'Yes' if public else 'No'} |"
                )
    lines.extend(row for _key, row in sorted(entries.items()))
    lines.append("")
    return "\n".join(lines)
