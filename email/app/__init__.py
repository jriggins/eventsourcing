from distutils.log import error
from functools import singledispatchmethod
from typing import Tuple
from uuid import UUID

from eventsourcing.application import Application
from eventsourcing.domain import Aggregate, AggregateEvent, event
from eventsourcing.system import ProcessApplication, System, MultiThreadedRunner, ProcessEvent, Runner
from eventsourcing.utils import Environment
from flask import Flask, jsonify, request

##############
# Domain Logic
##############

class EmailMessage(Aggregate):
    class Initiated(Aggregate.Created):
        to: str
        from_: str
        subject: str
        body: str

    class Sending(AggregateEvent):
        client_id: str

    class Sent(AggregateEvent):
        pass

    class Errored(AggregateEvent):
        error_message: str

    def __init__(self, to: str, from_: str, subject: str, body: str):
        self.to = to
        self.from_ = from_
        self.subject = subject
        self.body = body
        self.status = "INITIATED"
        self.error_message = None

    @event(Sending)
    def email_sending(self, client_id: str):
        self.status = "SENDING"
        self.client_id = client_id

    @event(Sent)
    def email_sent(self):
        self.status = "SENT"

    @event(Errored)
    def email_errored(self, error_message: str):
        self.status = "ERRORED"
        self.error_message = error_message

class EmailApp(ProcessApplication):
    def send_email(self, to: str, from_: str, subject: str, body: str):
        email_message = EmailMessage(to=to, from_=from_, subject=subject, body=body)
        self.save(email_message)
        return email_message.id

    def get_email_message(self, id: UUID) -> EmailMessage:
        return self.repository.get(id)

    @singledispatchmethod
    def policy(self, domain_event, process_event):
        pass

    @policy.register(EmailMessage.Initiated)
    def _(self, domain_event: EmailMessage.Initiated, process_event: ProcessEvent):
        email_message = self.repository.get(domain_event.originator_id)
        self._send_email(email_message)
        process_event.collect_events(*email_message.collect_events())

    @policy.register(EmailMessage.Sending)
    def _(self, domain_event: EmailMessage.Sending, process_event: ProcessEvent):
        email_message = self.repository.get(domain_event.originator_id)
        self._email_client: EmailClient = self.env["EMAIL_CLIENT"]
        try:
            email_status = self._email_client.get_send_email_status(email_message.client_id)
            if email_status["status"] == "SENT":
                email_message.email_sent()
            elif email_status["status"] == "ERRORED":
                email_message.email_errored(email_status["error_message"])
            else:
                email_message.email_errored("UNKNOWN")
        except Exception as e:
            email_message.email_errored(str(e))

        process_event.collect_events(*email_message.collect_events())

    def _send_email(self, email_message: EmailMessage):
        self._email_client: EmailClient = self.env["EMAIL_CLIENT"]
        try:
            result = self._email_client.send_email()
            email_message.email_sending(result["id"])
        except Exception as e:
            email_message.email_errored(str(e))


class EmailClient:
    def send_email(email_message: EmailMessage):
        return {
            "id": "ae55bc81-cafb-42d6-9c9f-2eb7cda6e528"
        }
    def get_send_email_status(self, id: UUID):
        return {
            "status": "SENT"
        }

###############
# Web App Logic
###############

def start_event_sourcing_system() -> Runner:
    import os
    environ = Environment()
    environ["PERSISTENCE_MODULE"] = os.environ.get("EVENTSOURCING_PERSISTENCE_MODULE", "eventsourcing.sqlite")
    environ["SQLITE_DBNAME"] = ":memory:"
    # environ["SQLITE_DBNAME"] = "file::memory:?mode=memory&cache=shared"
    environ["SQLITE_LOCK_TIMEOUT"] = "10"
    environ["EMAIL_CLIENT"] = EmailClient()

    system = System([
        [EmailApp, EmailApp],
    ])
    runner = MultiThreadedRunner(system=system, env=environ)
    runner.start()

    return runner

def create_app() -> Tuple[Flask, EmailApp, Runner]:
    event_sourcing_runner = start_event_sourcing_system()
    flask_app = Flask(__name__)
    email_app = event_sourcing_runner.get(EmailApp)

    @flask_app.route("/email", methods=["POST"])
    def send_email():
        email_message_id = email_app.send_email(**request.json)
        location = f"/email/{email_message_id}"

        return "", 202, {"Location": location}

    @flask_app.route("/email/<uuid:id>", methods=["GET"])
    def get_sent_email_status(id: UUID):
        email_message = email_app.get_email_message(id)

        response = {
            "to": email_message.to,
            "from_": email_message.from_,
            "subject": email_message.subject,
            "body": email_message.body,
            "status": email_message.status,
        }

        if email_message.status == "ERRORED":
            response["error_message"] = email_message.error_message

        return jsonify(response)

    return flask_app, email_app, event_sourcing_runner
