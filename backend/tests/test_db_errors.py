from app.db import explain_connection_error

URL = "postgresql://stocklens:stocklens@localhost:5432/stocklens"


def test_wrong_password_is_explained():
    msg = explain_connection_error(URL, Exception('FATAL:  password authentication failed for user "stocklens"'))
    assert "rejected the user name or password" in msg and "Database setup" in msg and "localhost:5432" in msg


def test_missing_database_is_explained():
    msg = explain_connection_error(URL, Exception('FATAL:  database "stocklens" does not exist'))
    assert "CREATE DATABASE stocklens" in msg


def test_server_down_is_explained():
    msg = explain_connection_error(URL, Exception("connection refused"))
    assert "Can't reach PostgreSQL" in msg
