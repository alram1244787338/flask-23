import pytest
from flask import g
from flask import session

from flaskr.db import get_db


def test_register(client, app):
    # test that viewing the page renders without template errors
    assert client.get("/auth/register").status_code == 200

    # test that successful registration redirects to the login page
    response = client.post("/auth/register", data={"username": "a", "password": "a"})
    assert response.headers["Location"] == "/auth/login"

    # test that the user was inserted into the database
    with app.app_context():
        assert (
            get_db().execute("SELECT * FROM user WHERE username = 'a'").fetchone()
            is not None
        )


@pytest.mark.parametrize(
    ("username", "password", "message"),
    (
        ("", "", b"Username is required."),
        ("a", "", b"Password is required."),
        ("test", "test", b"already registered"),
    ),
)
def test_register_validate_input(client, username, password, message):
    response = client.post(
        "/auth/register", data={"username": username, "password": password}
    )
    assert message in response.data


def test_login(client, auth):
    # test that viewing the page renders without template errors
    assert client.get("/auth/login").status_code == 200

    # test that successful login redirects to the index page
    response = auth.login()
    assert response.headers["Location"] == "/"

    # login request set the user_id in the session
    # check that the user is loaded from the session
    with client:
        client.get("/")
        assert session["user_id"] == 1
        assert g.user["username"] == "test"


@pytest.mark.parametrize(
    ("username", "password", "message"),
    (("a", "test", b"Incorrect username."), ("test", "a", b"Incorrect password.")),
)
def test_login_validate_input(auth, username, password, message):
    response = auth.login(username, password)
    assert message in response.data


def test_logout(client, auth):
    auth.login()

    with client:
        auth.logout()
        assert "user_id" not in session


def test_register_normalizes_username(client, app):
    # surrounding whitespace and casing are stripped before storing
    response = client.post(
        "/auth/register", data={"username": "  Spaced  ", "password": "x"}
    )
    assert response.headers["Location"] == "/auth/login"

    with app.app_context():
        db = get_db()
        # the canonical (trimmed, case-folded) name is what gets stored ...
        assert (
            db.execute("SELECT * FROM user WHERE username = 'spaced'").fetchone()
            is not None
        )
        # ... and the raw, un-normalized value is never persisted
        assert (
            db.execute("SELECT * FROM user WHERE username = '  Spaced  '").fetchone()
            is None
        )


def test_register_duplicate_is_case_insensitive(client):
    # "test" already exists in the seed data, so "TEST" must collide with it
    response = client.post(
        "/auth/register", data={"username": "TEST", "password": "x"}
    )
    assert b"already registered" in response.data


def test_register_whitespace_username_required(client):
    # a username made up only of whitespace is treated as missing
    response = client.post(
        "/auth/register", data={"username": "   ", "password": "x"}
    )
    assert b"Username is required." in response.data


def test_login_normalizes_username(client, auth):
    # the seeded user is "test"; logging in with padding and caps still works
    response = auth.login("  TEST  ", "test")
    assert response.headers["Location"] == "/"

    with client:
        client.get("/")
        assert session["user_id"] == 1
        assert g.user["username"] == "test"


def test_login_whitespace_username_required(auth):
    # a blank username reports "required" rather than "Incorrect username."
    response = auth.login("   ", "test")
    assert b"Username is required." in response.data
