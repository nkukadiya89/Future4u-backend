from django import template

register = template.Library()


@register.filter
def get_item(dct, key):
    if dct is None:
        return None
    try:
        return dct.get(key)
    except Exception:
        return None

