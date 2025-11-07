import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')


app = Celery("backend")
app.config_from_object("django.conf:settings", namespace="CELERY")

# ✅ так Celery найдёт tasks во всех приложениях из INSTALLED_APPS
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # ✅ импортируем объект функции и вызываем напрямую — без строкового имени
    from kbrs_api.tasks.congratulations import send_birthday_congratulations

    # 1) однократно при старте воркера (как ты хотел сейчас)
    # send_birthday_congratulations.delay()

    # 2) пример расписания на будущее (включишь позже вместе с celery beat)
    sender.add_periodic_task(
        crontab(hour=9, minute=0),  # 09:00 UTC
        send_birthday_congratulations.s(),
        name='daily-birthday-check',
    )
