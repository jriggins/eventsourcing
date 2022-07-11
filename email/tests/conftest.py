from typing import Tuple
import pytest

from flask import Flask
from flask.testing import FlaskClient

from app import EmailApp, Runner

@pytest.fixture()
def apps() -> Tuple[Flask, EmailApp, Runner]:
    from app import create_app
    flask_app, email_app, event_sourcing_runner = create_app()

    return {
        "flask_app": flask_app,
        "email_app": email_app,
        "event_sourcing_runner": event_sourcing_runner
    }

@pytest.fixture()
def flask_app(apps) -> Flask:
    try:
        yield apps["flask_app"]
    finally:
        apps["event_sourcing_runner"].stop()

@pytest.fixture()
def test_client(flask_app: Flask) -> FlaskClient:
    return flask_app.test_client()

@pytest.fixture()
def event_sourcing_runner(apps) -> Runner:
    return apps["event_sourcing_runner"]
