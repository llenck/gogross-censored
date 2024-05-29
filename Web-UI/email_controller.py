import smtplib, json
from email.message import EmailMessage

class Email_Controller:
    sender, host, port = None, None, None

    @staticmethod
    def get_settings():
        return {
            "address": Email_Controller.sender,
            "host": Email_Controller.host,
            "port": Email_Controller.port
        }

    @staticmethod
    def update_settings(sender=None, port=None, host=None):
        if not sender is None:
            Email_Controller.host = host
        if not port is None:
            Email_Controller.port = port
        if not host is None:
            Email_Controller.sender = sender

        json.dump(Email_Controller.get_settings(),
                  open("persist/email_config.json", "w"))

    # attachments: dictionary of PDFs. If we want more types, we must add mimetypes as
    # attachment arguments.
    @staticmethod
    def send(recipient, subject, content, attachments={}):
        msg = EmailMessage()
        msg['From'] = Email_Controller.sender
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.set_content(content)

        for (file_name, file_content) in attachments.items():
            msg.add_attachment(file_content, filename=file_name, maintype="application",
                               subtype="pdf")

        try:
            with smtplib.SMTP(Email_Controller.host, Email_Controller.port) as smtp:
                smtp.send_message(msg)
                return True
        except Exception as e:
            print("[WARN] on sending email:", e)
            return False

# try loading persistet config, use default if not available
try:
    email_config = json.load(open("persist/email_config.json"))
except FileNotFoundError:
    email_config = {
        "address": "gogross_support@gogross.com",
        "host": "localhost",
        "port": 8025
    }
Email_Controller.sender = email_config["address"]
Email_Controller.host = email_config["host"]
Email_Controller.port = email_config["port"]
