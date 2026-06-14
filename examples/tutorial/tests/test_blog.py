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
    response = client.post("/1/update")
    assert response.status_code == 403
    # the forbidden page makes clear this is a permission problem, which
    # is different from the post not existing
    assert b"Back to all posts" in response.data
    assert b"posts that you authored" in response.data
    assert client.post("/1/delete").status_code == 403
    # current user doesn't see edit link
    assert b'href="/1/update"' not in client.get("/").data


@pytest.mark.parametrize("path", ("/2/update", "/2/delete"))
def test_exists_required(client, auth, path):
    auth.login()
    response = client.post(path)
    assert response.status_code == 404
    # a missing post shows the friendly not-found page, not a dead click
    assert b"Back to all posts" in response.data


def test_create(client, auth, app):
    auth.login()
    assert client.get("/create").status_code == 200
    client.post("/create", data={"title": "created", "body": ""})

    with app.app_context():
        db = get_db()
        count = db.execute("SELECT COUNT(id) FROM post").fetchone()[0]
        assert count == 2


def test_create_strips_title(client, auth, app):
    auth.login()
    # surrounding whitespace is trimmed before the post is saved
    client.post("/create", data={"title": "  spaced title  ", "body": ""})

    with app.app_context():
        db = get_db()
        post = db.execute(
            "SELECT * FROM post WHERE title = 'spaced title'"
        ).fetchone()
        assert post is not None


def test_update(client, auth, app):
    auth.login()
    assert client.get("/1/update").status_code == 200
    client.post("/1/update", data={"title": "updated", "body": ""})

    with app.app_context():
        db = get_db()
        post = db.execute("SELECT * FROM post WHERE id = 1").fetchone()
        assert post["title"] == "updated"


@pytest.mark.parametrize("path", ("/create", "/1/update"))
@pytest.mark.parametrize("title", ("", "   ", "\n\t "))
def test_create_update_validate(client, auth, path, title):
    auth.login()
    # empty titles and whitespace-only titles are both rejected, and
    # create and update reject them the same way
    response = client.post(path, data={"title": title, "body": ""})
    assert b"Title is required." in response.data


def test_delete(client, auth, app):
    auth.login()
    response = client.post("/1/delete")
    assert response.headers["Location"] == "/"

    with app.app_context():
        db = get_db()
        post = db.execute("SELECT * FROM post WHERE id = 1").fetchone()
        assert post is None
