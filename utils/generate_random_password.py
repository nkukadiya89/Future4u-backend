import random
import string


def generate_random_password(self):
    password_length = 10
    characters = string.ascii_letters + string.digits + string.punctuation
    random_password = "".join(random.choice(characters) for i in range(password_length))
    return random_password
