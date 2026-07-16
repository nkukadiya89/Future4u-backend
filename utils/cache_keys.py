def dropdown_key(model_name: str) -> str:
    return f"dropdown:{model_name}"


def recommendation_key(user_id: int) -> str:
    return f"recommendation:{user_id}"


def job_search_key(title: str, location: str, page: int) -> str:
    """Cache key for LinkedIn job search results."""
    title = title.lower().strip() if title else ""
    location = location.lower().strip() if location else ""
    return f"jobs:search:{title}:{location}:{page}"
