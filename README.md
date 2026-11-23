# SubWatch

**Учёт подписок и анализ регулярных расходов.** SubWatch собирает платные сервисы в одном месте, показывает месячную и годовую нагрузку, напоминает о предстоящих списаниях и сохраняет историю платежей и изменения стоимости.

> Статус: первая версия находится в разработке. Инструкция ниже описывает локальный запуск; публичный адрес появится после отдельного деплоя.

## Возможности

- регистрация и личный кабинет;
- CRUD собственных подписок с периодичностью, валютой и датой следующего платежа;
- месячный эквивалент и годовой прогноз;
- конвертация сумм через Frankfurter API v2 с сохранением снимков курсов;
- ближайшие списания и пользовательские напоминания;
- приостановка и возобновление подписки через AJAX/Fetch без перезагрузки страницы;
- история платежей и изменений стоимости;
- аналитика по месяцам и категориям на Pandas + Chart.js;
- Django Admin для всех предметных моделей;
- REST API с авторизацией, пагинацией, поиском и изоляцией пользовательских данных.

## Технологии

- Python 3.12+
- Django 5.2 LTS
- SQLite (локально) / PostgreSQL (через `DATABASE_URL`)
- Requests, Frankfurter API v2, Pandas, Django REST Framework 3.18
- Bootstrap 5, Chart.js, собственные CSS/JavaScript
- WhiteNoise для статических файлов

## Локальный запуск (macOS / Linux)

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

Откройте `http://127.0.0.1:8000/`. Для наполнения демонстрационными данными сначала зарегистрируйте пользователя, затем выполните:

```bash
python manage.py load_demo_data --username <ваш_username>
```

## Переменные окружения

Скопируйте `.env.example` в `.env`. Для production обязательно задайте случайный `DJANGO_SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` и `DATABASE_URL` (при использовании PostgreSQL). Не коммитьте `.env`.

## Проверка

Проект содержит 22 теста бизнес-логики, пользовательской изоляции, REST API и аналитики. Для локальной проверки установите инструменты разработки и выполните:

```bash
pip install -r requirements-dev.txt
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

## Напоминания по email

Команда проверяет, какие напоминания наступили сегодня, и отправляет письма на адрес пользователя:

```bash
python manage.py send_subscription_reminders --dry-run
python manage.py send_subscription_reminders
```

На хостинге команду следует запускать ежедневно через планировщик (например, PythonAnywhere Tasks). Для реальной отправки задайте SMTP-переменные `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` и `DEFAULT_FROM_EMAIL`. Без SMTP письма выводятся в консоль.

## Деплой

Проект подготовлен к WSGI-развёртыванию. Пошаговая инструкция находится в [`docs/DEPLOY_PYTHONANYWHERE.md`](docs/DEPLOY_PYTHONANYWHERE.md). В production необходимо задать `DEBUG=False`, уникальный `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, настроить HTTPS, выполнить `migrate` и `collectstatic`.

## Скриншоты

Скриншоты главной панели, списка подписок и аналитики будут добавлены в `docs/screenshots/` после запуска интерфейса в браузере.

## Внешние данные

Курсы валют загружаются через [Frankfurter API](https://frankfurter.dev/). Это справочные курсы, а не гарантированные курсы банковских списаний. Источник Frankfurter, исходная валюта, сумма пересчёта и дата применённого курса сохраняются в записи платежа; при недоступности API приложение использует последний сохранённый снимок, если он есть.

## Лицензия

Учебный проект. Лицензию можно выбрать перед публикацией репозитория.

## REST API

Все API endpoints требуют авторизации. При использовании браузера применяется сессионная аутентификация; для автоматизированных клиентов доступна HTTP Basic Authentication по HTTPS.

| Метод | Endpoint | Назначение |
|---|---|---|
| GET, POST | `/api/v1/subscriptions/` | Список своих подписок и создание |
| GET, PATCH, DELETE | `/api/v1/subscriptions/<id>/` | Просмотр, изменение и удаление своей подписки |
| GET | `/api/v1/payments/` | История платежей своего аккаунта |
| GET | `/api/v1/categories/` | Справочник категорий |

Список подписок поддерживает параметры `search`, `status`, `category` и `ordering`. Пример: `/api/v1/subscriptions/?status=active&ordering=next_payment_date`.

API реализовано на Django REST Framework; владелец подписки назначается сервером из `request.user`, а queryset ограничен текущим пользователем.
