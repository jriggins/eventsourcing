from time import sleep
from unittest.mock import patch

from flask.testing import FlaskClient

# Uncomment to see the difference in behavior
# import os
# os.environ["EVENTSOURCING_PERSISTENCE_MODULE"] = "eventsourcing.popo"

class TestWebApp:
    def test_works(self, test_client: FlaskClient):
        """
        Given a /email endpoint
        When I POST a Send Email Message request to the endpoint
        Then I receive a 202 Accepted response with a URL to retrieve the command's
          status in the Location header (and annoying some REST purists 😅)
        """
        with patch('app.EmailMessage.create_id') as stub_create_email_message_id:
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
