from time import sleep
from unittest.mock import patch

from flask.testing import FlaskClient

from app import EmailApp, Runner

# Uncomment to see the difference in behavior
# import os
# os.environ["EVENTSOURCING_PERSISTENCE_MODULE"] = "eventsourcing.popo"

class TestWebApp:
    @patch('app.EmailMessage.create_id')
    def test_works(self, stub_create_email_message_id, test_client: FlaskClient):
        """
        Given a /email endpoint
        When I POST a Send Email Message request to the endpoint
        And the 3rd Party Email Service successfully sends the message
        Then I receive a 202 Accepted response with a URL to retrieve the command's
          status in the Location header (and annoying some REST purists 😅)
        And the returned status from the endpoint is SENT
        """
        # with patch('app.EmailMessage.create_id') as stub_create_email_message_id:
        from uuid import UUID
        stub_create_email_message_id.return_value = UUID("85ad5a4e-ff27-11ec-a0f1-0242ac140006")

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
        assert {
            "to": "test_recipient@example.com",
            "from_": "test_sender@example.com",
            "subject": "Test Message",
            "body": "This is only a test",
            "status": "SENT"
        } == response.json

    @patch('app.EmailMessage.create_id')
    def test_fails(self, stub_create_email_message_id, test_client: FlaskClient, event_sourcing_runner: Runner):
        """
        Given a /email endpoint
        When I POST a Send Email Message request to the endpoint
        But the 3rd Party Email Service fails to send the message
        Then I receive a 202 Accepted response with a URL to retrieve the command's
          status in the Location header
        And the returned status from the endpoint is ERRORED with an error message
        """
        from uuid import UUID
        stub_create_email_message_id.return_value = UUID("8f86530e-4fcc-4544-b493-684faa626c70")

        email_client = event_sourcing_runner.get(EmailApp).env["EMAIL_CLIENT"]
        email_client.get_send_email_status = lambda id: {
            "status": "ERRORED",
            "error_message": "BOOM!!"
        }

        response = test_client.post('/email', json={
            "to": "test_recipient@example.com",
            "from_": "test_sender@example.com",
            "subject": "Test Message",
            "body": "This is only a test"
        })
        assert 202 == response.status_code
        assert "/email/8f86530e-4fcc-4544-b493-684faa626c70" == response.headers['Location']

        sleep(0.5)

        response = test_client.get("/email/8f86530e-4fcc-4544-b493-684faa626c70")
        assert 200 == response.status_code
        assert {
            "to": "test_recipient@example.com",
            "from_": "test_sender@example.com",
            "subject": "Test Message",
            "body": "This is only a test",
            "status": "ERRORED",
            "error_message": "BOOM!!"
        } == response.json
