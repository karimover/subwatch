# SubWatch

SubWatch — веб-приложение для учёта подписок и анализа регулярных расходов. Сервис объединяет платные сервисы в одном месте, показывает месячную и годовую финансовую нагрузку, напоминает о предстоящих списаниях и сохраняет историю платежей и изменений стоимости.

## Возможности

- личные кабинеты и изоляция пользовательских данных;
- управление подписками с периодичностью, валютой и датой следующего платежа;
- расчёт месячного эквивалента и годового прогноза;
- конвертация сумм через Frankfurter API v2;
- напоминания о предстоящих списаниях и email-уведомления;
- история платежей и изменения стоимости;
- аналитика расходов по месяцам и категориям;
- REST API на Django REST Framework;
- административная панель Django.

## Стек

Python 3.12+, Django 5.2 LTS, SQLite для локальной разработки, PostgreSQL для production, Requests, Frankfurter API v2, Pandas, Django REST Framework, Bootstrap 5, Chart.js и WhiteNoise.

## Статус

Первая версия проекта опубликована для дальнейшей разработки. Django-тесты и production-развёртывание должны быть проверены отдельно в CI и на хостинге. См. [QA_STATUS](docs/QA_STATUS.md).

## Локальный запуск

```bash
git clone https://github.com/karimover/subwatch.git
cd subwatch
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Откройте http://127.0.0.1:8000/. После регистрации можно загрузить демонстрационные данные:

```bash
python manage.py load_demo_data --username <your_username>
```

## Проверки

```bash
pip install -r requirements-dev.txt
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

## Документация

- [Техническое задание](TZ.md)
- [Инструкция по деплою на PythonAnywhere](docs/DEPLOY_PYTHONANYWHERE.md)
- [Статус контроля качества](docs/QA_STATUS.md)

## Внешние данные

Курсы валют загружаются через [Frankfurter API](https://frankfurter.dev/). Это справочные курсы, они могут отличаться от банковского курса конкретного платежа. При недоступности API приложение может использовать последний сохранённый снимок курса, если он имеется.

## Безопасность

Не публикуйте файл `.env`, секретный ключ Django, SMTP-пароли или production credentials. Для production задайте `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DJANGO_SECRET_KEY` и `DATABASE_URL`.

## Лицензия

Учебный проект. Лицензионные условия будут определены отдельно.
