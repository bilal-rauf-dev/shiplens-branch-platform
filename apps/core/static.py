"""Cache hashed assets for one year while leaving mutable URLs short-lived."""


def immutable_cache_headers(headers, path, url):
    """Replace WhiteNoise's ten-year immutable default with the planned one year."""
    if "immutable" in headers.get("Cache-Control", ""):
        headers["Cache-Control"] = "max-age=31536000, public, immutable"
