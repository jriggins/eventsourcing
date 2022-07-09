
from time import sleep
from unittest.mock import patch

from flask import Flask
from flask.testing import FlaskClient

class TestWebApp:
    def test_works(self, test_client: FlaskClient):
        # with patch('app.SendEmail.create_id') as stub_generate_uuid:
        with patch('app.EmailMessage.create_id') as stub_generate_uuid:
            from uuid import UUID
            stub_generate_uuid.return_value = UUID("85ad5a4e-ff27-11ec-a0f1-0242ac140006")

            response = test_client.post('/email', json={
                "to": "test_recipient@example.com",
                "from_": "test_sender@example.com",
                "subject": "Test Message",
                "body": "This is only a test"
            })
            assert 202 == response.status_code
            assert "/email/85ad5a4e-ff27-11ec-a0f1-0242ac140006" == response.headers['Location']

            sleep(0.5)
            response = test_client.get("/email/85ad5a4e-ff27-11ec-a0f1-0242ac140006")
            assert 200 == response.status_code
            assert "Test Message" == response.json['subject']
            assert "SENT" == response.json['status']
