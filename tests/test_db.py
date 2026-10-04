"""Tests for database auth: hashed passwords, legacy plaintext fallback, login."""

import os
import sqlite3

import pytest

import main
from main import hash_password, init_db, verify_login, verify_password


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


def test_passwords_are_hashed_not_plaintext(db_path):
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT password FROM users WHERE username='admin'").fetchone()
    conn.close()
    stored = row[0]
    assert "$" in stored  # salt$digest format
    assert "123456" not in stored


def test_passwords_unique_salts(db_path):
    """Every user gets a distinct salt, so identical passwords hash differently."""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    pwds = [r[0] for r in conn.execute("SELECT password FROM users").fetchall()]
    conn.close()
    assert len(set(pwds)) == len(pwds)


def test_hash_password_deterministic_with_fixed_salt():
    a = hash_password("secret", salt="somesalt")
    b = hash_password("secret", salt="somesalt")
    assert a == b


def test_hash_password_random_salts_differ():
    assert hash_password("secret") != hash_password("secret")


def test_verify_login_success_admin(db_path):
    init_db(db_path)
    assert verify_login("admin", "123456", db_path) == "admin"


def test_verify_login_success_user(db_path):
    init_db(db_path)
    assert verify_login("user", "123456", db_path) == "user"


def test_verify_login_wrong_password(db_path):
    init_db(db_path)
    assert verify_login("admin", "wrong", db_path) is None


def test_verify_login_unknown_user(db_path):
    init_db(db_path)
    assert verify_login("nobody", "123456", db_path) is None


def test_verify_password_legacy_plaintext_fallback():
    """Old databases stored plaintext — verify_password still accepts them."""
    assert verify_password("123456", "123456") is True
    assert verify_password("123456", "wrong") is False


def test_verify_login_works_on_legacy_plaintext_db(tmp_path):
    """A pre-existing plaintext DB (from before the hashing change) still logs in."""
    legacy = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(legacy)
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL)"
    )
    conn.execute("INSERT INTO users (username, password, role) VALUES ('admin', '123456', 'admin')")
    conn.commit()
    conn.close()
    assert verify_login("admin", "123456", legacy) == "admin"
    assert verify_login("admin", "nope", legacy) is None


def test_init_db_seeds_default_users(db_path):
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    roles = dict(conn.execute("SELECT username, role FROM users").fetchall())
    conn.close()
    assert roles == {"admin": "admin", "user": "user"}


def test_db_path_resolves_under_base_dir():
    """DB_PATH defaults to <repo>/system.db (or honors PYOLDOS_DB)."""
    expected = os.environ.get("PYOLDOS_DB") or os.path.join(main.BASE_DIR, "system.db")
    assert main.DB_PATH == expected