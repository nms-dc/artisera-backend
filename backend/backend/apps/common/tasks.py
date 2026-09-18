from celery import shared_task
import time


@shared_task
def mock_slow_task(name):
    time.sleep(5)
    print(f"Task finished for {name}")
    return f"Hello, {name}!"