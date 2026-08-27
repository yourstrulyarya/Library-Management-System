"""
auth.py — simple username/password authentication for the Librarian
account. Credentials live in data/users.json with hashed passwords (never
plaintext). This is intentionally lightweight for a local college project:
one shared Librarian account, no registration flow, no password reset —
not meant to be internet-facing production auth.
"""

from werkzeug.security import check_password_hash
from utils.json_utils import read_json

FILE = "users.json"


def get_user(user_id):
    user_id = (user_id or "").strip().lower()
    for u in read_json(FILE):
        if u.get("user_id", "").lower() == user_id:
            return u
    return None


def verify_login(user_id, password):
    """Returns (user, None) on success or (None, error_message) on failure."""
    user = get_user(user_id)
    if not user:
        return None, "No account found with that User ID."
    if not check_password_hash(user.get("password_hash", ""), password or ""):
        return None, "Incorrect password."
    return user, None
