from celery import shared_task
import time


@shared_task
def mock_slow_task(name):
    time.sleep(5)
    print(f"Task finished for {name}")
    return f"Hello, {name}!"

@shared_task
def send_email_mockup(email):
    time.sleep(5)
    print(f"trying to send invitation to {email}")
    return f"link to login sent to {email}"