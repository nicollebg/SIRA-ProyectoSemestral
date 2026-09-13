"""
security.py
Utilidades de autenticación: hash y verificación de contraseñas con
PBKDF2-HMAC-SHA256 (no se guardan contraseñas en texto plano).
"""

import hashlib
import os

_ITERACIONES = 100_000


def hash_password(password: str) -> str:
    """Genera 'salt:hash' listo para guardar en la base de datos."""
    salt = os.urandom(16)
    derivado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERACIONES)
    return f"{salt.hex()}:{derivado.hex()}"


def verify_password(password: str, almacenado: str) -> bool:
    """Verifica una contraseña contra el valor 'salt:hash' guardado."""
    try:
        salt_hex, hash_hex = almacenado.split(":")
    except (ValueError, AttributeError):
        return False
    salt = bytes.fromhex(salt_hex)
    derivado = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERACIONES)
    return derivado.hex() == hash_hex
