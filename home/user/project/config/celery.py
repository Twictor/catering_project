import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config',
             broker='redis://localhost:6379/0',  # Replace with your Redis broker URL
             backend='redis://localhost:6379/0',  # Replace with your Redis backend URL
             include=['users.tasks'])

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
