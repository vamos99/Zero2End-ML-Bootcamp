DEFAULT_TOP_N = 10
MAX_TOP_N = 100


def clamp_limit(value, default=DEFAULT_TOP_N, maximum=MAX_TOP_N):
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return default

    if limit < 1:
        return default
    return min(limit, maximum)
