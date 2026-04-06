def dropdown_key(model_name: str) -> str:
    return f"dropdown:{model_name}"


def recommendation_key(user_id: int) -> str:
    return f"recommendation:{user_id}"
