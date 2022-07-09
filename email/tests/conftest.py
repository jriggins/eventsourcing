import pytest
from flask import Flask
from flask.testing import FlaskClient

@pytest.fixture()
def flask_app() -> Flask:
    from app import flask_app
    yield flask_app

@pytest.fixture()
def test_client(flask_app: Flask) -> FlaskClient:
    return flask_app.test_client()
