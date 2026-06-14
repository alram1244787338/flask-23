import pytest

from flaskr.db import get_db


def test_index(client, auth):
    response = client.get("/")
    assert b"Log In" in response.data
    assert b"Register" in response.data

    auth.login()
    response = client.get("/")
    assert b"test title" in response.data
    assert b"by test on 2018-01-01" in response.data
    assert b"test\nbody" in response.data
    assert b'href="/1/update"' in response.data


@pytest.mark.parametrize("path", ("/create", "/1/update", "/1/delete"))
def test_login_required(client, path):
    response = client.post(path)
    assert response.headers["Location"] == "/auth/login"


def test_author_required(app, client, auth):
    # change the post author to another user
    with app.app_context():
        db = get_db()
        db.execute("UPDATE post SET author_id = 2 WHERE id = 1")
        db.commit()

    auth.login()
    # current user can't modify other user's post
    assert client.post("/1/update").status_code == 403
    assert client.post("/1/delete").status_code == 403
    # current user doesn't see edit link
    assert b'href="/1/update"' not in client.get("/").data


@pytest.mark.parametrize("path", ("/2/update", "/2/delete"))
def test_exists_required(client, auth, path):
    auth.login()
    assert client.post(path).status_code == 404


def test_create(client, auth, app):
    auth.login()
    assert client.get("/create").status_code == 200
    client.post("/create", data={"title": "created", "body": ""})

    with app.app_context():
        db = get_db()
        count = db.execute("SELECT COUNT(id) FROM post").fetchone()[0]
        assert count == 2


def test_update(client, auth, app):
    auth.login()
    assert client.get("/1/update").status_code == 200
    client.post("/1/update", data={"title": "updated", "body": ""})

    with app.app_context():
        db = get_db()
        post = db.execute("SELECT * FROM post WHERE id = 1").fetchone()
        assert post["title"] == "updated"


@pytest.mark.parametrize("path", ("/create", "/1/update"))
def test_create_update_validate(client, auth, path):
    auth.login()
    response = client.post(path, data={"title": "", "body": ""})
    assert b"Title is required." in response.data


@pytest.mark.parametrize(
    "bad_title",
    ("   ", "\t", "\n", "  \n\t  "),
)
@pytest.mark.parametrize("path", ("/create", "/1/update"))
def test_create_update_whitespace_title(client, auth, path, bad_title):
    auth.login()
    response = client.post(path, data={"title": bad_title, "body": "some body"})
    assert b"Title is required." in response.data


def test_update_no_permission(app, client, auth):
    """Trying to edit another user's post should return 403 with a clear message."""
    # Reassign post 1 to user 2 so that the logged-in user (test, id=1)
    # is no longer the author.
    with app.app_context():
        db = get_db()
        db.execute("UPDATE post SET author_id = 2 WHERE id = 1")
        db.commit()

    auth.login()
    response = client.post("/1/update", data={"title": "hacked", "body": ""})
    assert response.status_code == 403
    assert b"permission" in response.data


def test_delete_no_permission(app, client, auth):
    """Trying to delete another user's post should return 403 with a clear message."""
    with app.app_context():
        db = get_db()
        db.execute("UPDATE post SET author_id = 2 WHERE id = 1")
        db.commit()

    auth.login()
    response = client.post("/1/delete")
    assert response.status_code == 403
    assert b"permission" in response.data


def test_update_not_found(client, auth):
    """Updating a post that doesn't exist should return 404 with a clear message."""
    auth.login()
    response = client.post("/999/update", data={"title": "x", "body": ""})
    assert response.status_code == 404
    assert b"doesn&#39;t exist" in response.data or b"doesn" in response.data


def test_delete_not_found(client, auth):
    """Deleting a post that doesn't exist should return 404 with a clear message."""
    auth.login()
    response = client.post("/999/delete")
    assert response.status_code == 404
    assert b"doesn&#39;t exist" in response.data or b"doesn" in response.data


def test_create_strips_title(client, auth, app):
    """Leading/trailing whitespace in the title is stripped before storing."""
    auth.login()
    client.post("/create", data={"title": "  padded title  ", "body": ""})

    with app.app_context():
        db = get_db()
        post = db.execute(
            "SELECT title FROM post ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert post["title"] == "padded title"


def test_delete(client, auth, app):
    auth.login()
    response = client.post("/1/delete")
    assert response.headers["Location"] == "/"

    with app.app_context():
        db = get_db()
        post = db.execute("SELECT * FROM post WHERE id = 1").fetchone()
        assert post is None
