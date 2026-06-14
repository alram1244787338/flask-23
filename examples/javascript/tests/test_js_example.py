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
        client.get(path, follow_redirects=True)


@pytest.mark.parametrize("js", ("fetch", "xhr", "jquery"))
def test_page_reports_errors(client, js):
    """Every front end posts to /add and has a place to show an error."""
    body = client.get(f"/{js}", follow_redirects=True).get_data(as_text=True)
    assert '/add' in body
    assert 'id="error"' in body


@pytest.mark.parametrize(
    ("a", "b", "result"),
    (
        ("2", "3", 5),
        ("2.5", "3", 5.5),
        ("-1", "1", 0),
        ("2", "3.5", 5.5),
    ),
)
def test_add_valid(client, a, b, result):
    response = client.post("/add", data={"a": a, "b": b})
    assert response.status_code == 200
    data = response.get_json()
    assert data["result"] == result
    assert "error" not in data


@pytest.mark.parametrize(
    "data",
    (
        {"a": "", "b": "3"},
        {"a": "   ", "b": "3"},
        {"a": "abc", "b": "3"},
        {"a": "2", "b": ""},
        {"a": "2"},
        {},
        {"a": "inf", "b": "3"},
        {"a": "2", "b": "nan"},
    ),
)
def test_add_invalid_does_not_silently_default(client, data):
    response = client.post("/add", data=data)
    assert response.status_code == 400
    body = response.get_json()
    # The user must see an error instead of a silent 0 result.
    assert body["error"]
    assert "result" not in body


def test_add_result_overflow(client):
    response = client.post("/add", data={"a": "1e308", "b": "1e308"})
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]
    assert "result" not in body
