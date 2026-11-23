# Деплой SubWatch на PythonAnywhere

Инструкция рассчитана на отдельный публичный GitHub-репозиторий и PythonAnywhere Web App. Названия пунктов панели могут меняться, поэтому после установки проверяйте журнал ошибок приложения.

## 1. Подготовить production-переменные

В корне проекта на сервере создайте `.env` (он уже исключён из Git):

```dotenv
DJANGO_SECRET_KEY=<длинный-случайный-секрет>
DEBUG=False
ALLOWED_HOSTS=<username>.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://<username>.pythonanywhere.com
TIME_ZONE=Europe/Amsterdam
BASE_CURRENCY=EUR
```

Не используйте `dev-only-subwatch-secret-key` в production. Секреты и SMTP-пароль не добавляйте в GitHub.

## 2. Клонировать проект и установить зависимости

В Bash-консоли PythonAnywhere:

```bash
cd ~
git clone https://github.com/karimover/subwatch.git
cd subwatch
mkvirtualenv --python=/usr/bin/python3.12 subwatch
pip install -r requirements.txt
```

Выберите версию Python, которая доступна в панели PythonAnywhere и совпадает с выбранной версией Web App.

## 3. Подготовить базу и статику

```bash
python manage.py check --deploy
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

Для первичного наполнения демонстрационного аккаунта зарегистрируйте его на сайте или создайте пользователя в Django Admin, затем выполните:

```bash
python manage.py load_demo_data --username <demo_username>
```

Команда создаёт до 12 примерных подписок и историю платежей, не добавляя дубликаты при повторном запуске.

## 4. Настроить Web App и WSGI

Создайте Web App с ручной конфигурацией и выберите ту же версию Python, что использовалась для виртуального окружения. Укажите virtualenv:

```text
/home/<username>/.virtualenvs/subwatch
```

В WSGI-файле замените путь на фактический:

```python
import os
import sys

project_path = "/home/<username>/subwatch"
if project_path not in sys.path:
    sys.path.insert(0, project_path)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

В панели Static files добавьте:

| URL | Directory |
|---|---|
| `/static/` | `/home/<username>/subwatch/staticfiles` |

Медиа-загрузка пользовательских файлов в первой версии не используется.

## 5. Проверить production

- В `.env` установлено `DEBUG=False`.
- `ALLOWED_HOSTS` содержит точный домен.
- `CSRF_TRUSTED_ORIGINS` начинается с `https://`.
- Секретный ключ отличается от dev-значения.
- `collectstatic` выполнен после обновления исходников.
- `/static/` настроен на `staticfiles`.
- Главная страница, вход, создание подписки, история платежей и аналитика открываются.
- `/admin/` доступен администратору.
- Web App перезагружен, ошибки проверены в error log.

## 6. Ежедневная отправка напоминаний

В разделе Tasks создайте ежедневную задачу с командой (замените имя пользователя):

```bash
cd /home/<username>/subwatch && /home/<username>/.virtualenvs/subwatch/bin/python manage.py send_subscription_reminders
```

Для реальной доставки писем настройте SMTP-переменные в `.env`. До включения ежедневной задачи проверьте выборку в режиме `--dry-run`:

```bash
python manage.py send_subscription_reminders --dry-run
```

## 7. Обновление проекта

```bash
cd /home/<username>/subwatch
git pull
source /home/<username>/.virtualenvs/subwatch/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

Затем перезагрузите Web App в панели PythonAnywhere.
