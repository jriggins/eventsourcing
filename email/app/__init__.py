from functools import singledispatchmethod
from typing import Tuple
from uuid import UUID

from eventsourcing.application import Application
from eventsourcing.system import ProcessApplication, System, MultiThreadedRunner, ProcessEvent, Runner
from eventsourcing.domain import Aggregate, AggregateEvent, event
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
        pass

    class Sent(AggregateEvent):
        pass

    def __init__(self, to: str, from_: str, subject: str, body: str):
        self.to = to
        self.from_ = from_
        self.subject = subject
        self.body = body
        self.status = "INITIATED"

    @event(Sent)
    def email_sent(self):
        self.status = "SENT"

class EmailApp(Application):
    def send_email(self, to: str, from_: str, subject: str, body: str):
        email_message = EmailMessage(to=to, from_=from_, subject=subject, body=body)
        self.save(email_message)
        return email_message.id

    def get_email_message(self, id: UUID) -> EmailMessage:
        return self.repository.get(id)

class EmailClient:
    def send_email(email_message: EmailMessage):
        pass

    def get_send_email_status(self, id: UUID):
        pass

class EmailProcessor(ProcessApplication):
    @singledispatchmethod
    def policy(self, domain_event, process_event):
        pass

    @policy.register(EmailMessage.Initiated)
    def _(self, domain_event: EmailMessage.Initiated, process_event: ProcessEvent):
        email_message = self.repository.get(domain_event.originator_id)
        self.send_email(email_message)
        process_event.collect_events(*email_message.collect_events())

    def send_email(self, email_message: EmailMessage):
        # TODO: Call email API
        email_message.email_sent()

###############
# Web App Logic
###############

def start_event_sourcing_system() -> Runner:
    import os
    from eventsourcing.utils import Environment
    environ = Environment()
    environ["PERSISTENCE_MODULE"] = os.environ.get("EVENTSOURCING_PERSISTENCE_MODULE", "eventsourcing.sqlite")
    environ["SQLITE_DBNAME"] = "file::memory:?mode=memory&cache=shared"
    environ["SQLITE_LOCK_TIMEOUT"] = "10"

    system = System([
        [EmailApp, EmailProcessor],
    ])
    runner = MultiThreadedRunner(system=system, env=environ)
    runner.start()

    return runner

def create_app() -> Tuple[Flask, EmailApp]:
    event_sourcing_runner = start_event_sourcing_system()
    flask_app = Flask(__name__)
    email_app = event_sourcing_runner.get(EmailApp)

    return flask_app, email_app

flask_app, email_app = create_app()

@flask_app.route("/email", methods=["POST"])
def send_email():
    email_message_id = email_app.send_email(**request.json)
    location = f"/email/{email_message_id}"

    return "", 202, {"Location": location}

@flask_app.route("/email/<uuid:id>", methods=["GET"])
def get_sent_email_status(id: UUID):
    email_message = email_app.get_email_message(id)

    return jsonify({
        "to": email_message.to,
        "from_": email_message.from_,
        "subject": email_message.subject,
        "body": email_message.body,
        "status": email_message.status,
    })
