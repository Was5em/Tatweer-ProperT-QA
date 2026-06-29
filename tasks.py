from celery import Celery
import os
import sys

workspace = os.path.dirname(os.path.abspath(__file__))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

celery_broker = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery("qa_tasks", broker=celery_broker, backend=celery_backend)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.task
def run_analysis_task(item_id: int, file_path: str):
    from core import background_analysis
    print(f"Celery Worker starting analysis task for item {item_id} (file: {file_path})")
    background_analysis(item_id, file_path)
