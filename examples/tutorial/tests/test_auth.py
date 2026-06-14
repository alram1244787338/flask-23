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
        ("   ", "", b"Username is required."),
        ("a", "", b"Password is required."),
        ("test", "test", b"already registered"),
        (" Test ", "test", b"already registered"),
        ("TEST", "test", b"already registered"),
    ),
)
def test_register_validate_input(client, username, password, message):
    response = client.post(
        "/auth/register", data={"username": username, "password": password}
    )
    assert message in response.data


def test_register_strips_whitespace_and_lowercases(client, app):
    """Registering with extra whitespace / mixed case stores a normalized name."""
    response = client.post(
        "/auth/register", data={"username": "  NewUser  ", "password": "pw"}
    )
    assert response.headers["Location"] == "/auth/login"
    with app.app_context():
        row = get_db().execute(
            "SELECT username FROM user WHERE username = 'newuser'"
        ).fetchone()
        assert row is not None
        assert row["username"] == "newuser"


def test_register_duplicate_after_normalization(client):
    """'Test', 'TEST' and ' test ' should all collide with the existing 'test' user."""
    for variant in ("TEST", " Test ", "test"):
        response = client.post(
            "/auth/register", data={"username": variant, "password": "x"}
        )
        assert b"already registered" in response.data


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
    (
        ("a", "test", b"No account found with that username."),
        ("missing_user", "test", b"No account found with that username."),
        ("test", "a", b"Incorrect password."),
    ),
)
def test_login_validate_input(auth, username, password, message):
    response = auth.login(username, password)
    assert message in response.data


@pytest.mark.parametrize(
    "username",
    ("TEST", " Test ", "  test"),
)
def test_login_accepts_normalized_username(auth, username):
    """Login should succeed even if case / whitespace differ from the stored name."""
    response = auth.login(username, "test")
    assert response.headers["Location"] == "/"


def test_logout(client, auth):
    auth.login()

    with client:
        auth.logout()
        assert "user_id" not in session


def test_register_then_login_with_different_case(client):
    """Register with messy input, then log in with a differently-messy variant."""
    response = client.post(
        "/auth/register", data={"username": "  Alice  ", "password": "secret"}
    )
    assert response.headers["Location"] == "/auth/login"

    response = client.post(
        "/auth/login", data={"username": "ALICE", "password": "secret"}
    )
    assert response.headers["Location"] == "/"
