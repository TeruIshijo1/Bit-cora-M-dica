import re

PASSWORD_MESSAGE = "La contraseña debe tener al menos 8 caracteres, mayúscula, minúscula, número y símbolo."


def valid_password(password):
    return (len(password) >= 8 and re.search(r"[A-Z]", password) is not None
            and re.search(r"[a-z]", password) is not None
            and re.search(r"\d", password) is not None
            and re.search(r"[^A-Za-z0-9\s]", password) is not None)
