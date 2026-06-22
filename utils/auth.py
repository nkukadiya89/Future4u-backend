import re
import secrets
import string


def generate_temporary_password(length=12):
    characters = string.ascii_letters + string.digits + "!@#$%^&*"

    return "".join(secrets.choice(characters) for _ in range(length))


def validate_password_strength(password):
    errors = {}
    if not password:
        errors["password"] = "This field is required."
        return errors

    if not re.search(r"[A-Z]", password):
        errors["password"] = "Password must contain at least 1 uppercase letter."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors["password"] = "Password must contain at least 1 special character."
    if not re.search(r"[0-9]", password):
        errors["password"] = "Password must contain at least 1 number."
    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters."

    return errors


def is_web_source(source):
    return source == "web"
