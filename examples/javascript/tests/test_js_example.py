import pytest
from flask import template_rendered


@pytest.mark.parametrize(
    ("path", "template_name"),
    (
        ("/", "fetch.html"),
        ("/xhr", "xhr.html"),
        ("/fetch", "fetch.html"),
        ("/jquery", "jquery.html"),
    ),
)
def test_index(app, client, path, template_name):
    def check(sender, template, context):
        assert template.name == template_name

    with template_rendered.connected_to(check, app):
        client.get(path)


@pytest.mark.parametrize(
    "path",
    ("/xhr", "/fetch", "/jquery"),
)
def test_index_pages_load(client, path):
    """Each frontend variant page loads successfully."""
    response = client.get(path, follow_redirects=True)
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("a", "b", "result"),
    (
        (2, 3, 5),
        (2.5, 3, 5.5),
        (-1, 1, 0),
        (0, 0, 0),
        ("1e2", "0.5", 100.5),
    ),
)
def test_add_valid(client, a, b, result):
    response = client.post("/add", data={"a": a, "b": b})
    assert response.status_code == 200
    assert response.get_json()["result"] == result


@pytest.mark.parametrize(
    ("a", "b"),
    [
        pytest.param(None, 2, id="missing-a"),
        pytest.param(2, None, id="missing-b"),
        pytest.param(None, None, id="missing-both"),
        pytest.param("", 2, id="empty-a"),
        pytest.param(2, "", id="empty-b"),
        pytest.param("   ", 2, id="whitespace-a"),
        pytest.param(2, "   ", id="whitespace-b"),
        pytest.param("abc", 2, id="non-numeric-a"),
        pytest.param(2, "xyz", id="non-numeric-b"),
        pytest.param("1 2", 3, id="partial-number-a"),
        pytest.param("inf", 2, id="infinity-a"),
        pytest.param("-inf", 2, id="neg-infinity-a"),
        pytest.param("2", "nan", id="nan-b"),
        pytest.param("nan", "inf", id="nan-and-inf"),
    ],
)
def test_add_invalid(client, a, b):
    response = client.post("/add", data={"a": a, "b": b})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    assert "result" not in data


def test_add_error_message_not_empty(client):
    """Error messages should be user-readable, not empty."""
    response = client.post("/add", data={"a": "hello", "b": "world"})
    data = response.get_json()
    assert data["error"]
    assert len(data["error"]) > 5
