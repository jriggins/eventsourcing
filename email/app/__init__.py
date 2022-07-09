from functools import singledispatchmethod
from uuid import UUID

from eventsourcing.application import Application
from eventsourcing.system import ProcessApplication, System, SingleThreadedRunner, ProcessEvent
from eventsourcing.domain import Aggregate, AggregateEvent, event
from flask import Flask, jsonify, request

class SendEmail(Aggregate):
    class Initiated(Aggregate.Created):
        to: str
        from_: str
        subject: str
        body: str

    def __init__(self, to: str, from_: str, subject: str, body: str):
        self.to = to
        self.from_ = from_
        self.subject = subject
        self.body = body
        self.status = "INITIATED"

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

class EmailApp(ProcessApplication):
    # @singledispatchmethod
    # def policy(self, domain_event, process_event):
    #     pass

    # @policy.register(EmailMessage.Sent)
    # def (self, domain_event, process_event):

    def initiate_send_email(self, to: str, from_: str, subject: str, body: str):
        # command = SendEmail(to=to, from_=from_, subject=subject, body=body)
        command = EmailMessage(to=to, from_=from_, subject=subject, body=body)
        self.save(command)
        return command.id

    def get_send_email_command(self, id: UUID) -> SendEmail:
        return self.repository.get(id)

    @singledispatchmethod
    def policy(self, domain_event, process_event):
        pass

class EmailClient:
    def initiate_send_email(self, to: str, from_: str, subject: str, body: str):
        pass

    def get_send_email_status(self, id: UUID):
        pass

class EmailProcessor(ProcessApplication):
    @singledispatchmethod
    def policy(self, domain_event, process_event):
        pass

    # @policy.register(SendEmail.Initiated)
    # def _(self, domain_event: SendEmail.Initiated, process_event: ProcessEvent):
    @policy.register(EmailMessage.Initiated)
    def _(self, domain_event: EmailMessage.Initiated, process_event: ProcessEvent):
        """
        Respond to a SendEmail.Initiated event by sending an email request to the 3rd party
        API which in itself is async.
        """
        # try:
        #     email_message = self.repository.get(domain_event.originator_id)
        # except Exception as e:
        #     print(f"Exc: {e}")
        # else:
        #     # Already processed
        #     return

        # email_message = EmailMessage(
        #     to=domain_event.to,
        #     from_=domain_event.from_,
        #     subject=domain_event.subject,
        #     body=domain_event.body
        # )
        email_message = self.repository.get(domain_event.originator_id)
        self.send_email(email_message)
        process_event.collect_events(*email_message.collect_events())

    def send_email(self, email_message: EmailMessage):
        # TODO: Call email API
        email_message.email_sent()


def create_environment():
    from eventsourcing.utils import Environment
    environ = Environment()
    environ["PERSISTENCE_MODULE"] = "eventsourcing.sqlite"
    environ["SQLITE_DBNAME"] = "file::memory:?mode=memory&cache=shared"
    environ["SQLITE_LOCK_TIMEOUT"] = "10"
    return environ

def create_app():
    environ = create_environment()
    system = System([
        [EmailApp, EmailProcessor],
        [EmailProcessor, EmailApp],
    ])
    runner = SingleThreadedRunner(system=system, env=environ)
    runner.start()

    flask_app = Flask(__name__)
    flask_app.email_app: EmailApp = runner.get(EmailApp)

    return flask_app

flask_app = create_app()

@flask_app.route("/email", methods=["POST"])
def initiate_send_email():
    command_id = flask_app.email_app.initiate_send_email(**request.json)
    location = f"/email/{command_id}"

    return "", 202, {"Location": location}

@flask_app.route("/email/<uuid:id>", methods=["GET"])
def get_sent_email_status(id: UUID):
    command = flask_app.email_app.get_send_email_command(id)
    return jsonify(command.__dict__)
