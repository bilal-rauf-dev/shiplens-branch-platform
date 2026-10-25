"""Public audit API; models load only after Django initializes its app registry."""


def record(*args, **kwargs):
    from apps.audit.services import record as record_event

    return record_event(*args, **kwargs)
