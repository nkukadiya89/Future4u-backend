import secrets
import string
from datetime import date


def generate_ticket_id():
    N = 4
    res = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(N))
    today = date.today()
    month = today.month
    year = str(today.year)
    ticket = "{}{}{}".format(str(res), month, year[2:])
    return ticket
