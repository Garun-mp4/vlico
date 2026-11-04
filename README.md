# VLICO

Локальная серверная версия сайта: Django 5.2 LTS, PostgreSQL и Docker Compose. Milestone 2 добавляет кастомный кабинет и управляемое портфолио. Калькулятор и отправка форм следуют в milestone 3; текущая форма честно остаётся демонстрационной.

## Запуск на Windows

1. Перед запуском Docker Desktop на этом компьютере прочитать `C:\Users\admin\.codex\docs\docker-desktop-windows.md`. Убедиться, что `docker info` отвечает и на C: не менее 15 ГБ свободно.
2. Из корня проекта: `powershell -ExecutionPolicy Bypass -File scripts/init-local.ps1`. Скрипт создаёт `.env` со случайными секретами и сохраняет существующий файл без изменений.
3. `docker compose up -d --build --wait`
4. Открыть http://localhost:8000/. Диагностика: `docker compose ps`, `docker compose logs --tail=50 web`, http://localhost:8000/health/.

Порт доступен только на loopback компьютера. БД наружу не публикуется. Если порт занят, изменить WEB_PORT и соответствующие доверенные origins в `.env`.

Миграции и collectstatic выполняются перед стартом Gunicorn. После правки кода выполнить `docker compose up -d --build --wait`. После правки окружения пересоздать контейнер (`up -d`), одного restart недостаточно.

## Проверки

```powershell
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose exec web python manage.py test core
docker compose exec web python manage.py showmigrations
```

Новые миграции создаются в исходниках и коммитятся. Создание миграции внутри контейнера без копирования в `backend/core/migrations/` потеряет её при пересборке. Для дальнейшей разработки можно использовать временный bind mount backend; текущий образ намеренно воспроизводимый, без привязки к рабочей папке.

## Данные и безопасность

- `database`: PostgreSQL; `public_media`: подготовленные публичные фото; `private_media`: контакты и вложения проектов. Все три named volumes сохраняются при пересоздании контейнеров.
- Не использовать `docker compose down --volumes`: это удалит данные. Остановка: `docker compose stop`; повторный запуск: `docker compose up -d --wait`.
- Volume не является резервной копией. До production требуется отдельное копирование БД/медиа и проверка восстановления (milestone 5).
- Публичная раздача пользовательских media пока не включена. Приватные файлы не имеют публичного URL; будущий доступ только через авторизованную серверную проверку.
- `.env` исключён из Git и Docker build context. Токен Telegram не включён в настройки Django и не передаётся в браузер. В milestone 1 обращения к Telegram отсутствуют.
- Не публиковать вывод `docker compose config` и окружение контейнеров: они содержат секреты. Для проверки синтаксиса использовать `docker compose config --quiet`.
- APP_ENV: local/preview/production. DEBUG выключен во всех средах. Preview и local закрыты от индексации. Production требует HTTPS, отдельные секреты, разрешённые hosts/origins и настройки reverse proxy; текущий Compose предназначен для локального запуска.
- SITE_INDEXABLE пока не включать: robots и окончательные SEO-правила будут завершены в milestone 4/5.

## Структура

- `backend/`: Django, серверный шаблон главной, модели, миграции, проверки.
- `wireframe/assets`, `wireframe/styles.css`, `wireframe/main.js`: общие подготовленные ресурсы; Django обслуживает их через WhiteNoise с хешированными именами.
- `wireframe/index.html`: сохранённая статическая версия прежнего Vercel-preview. Новый HTML меняется в `backend/templates/site/home.html`; синхронизация legacy preview не является production-публикацией.
- `from-client/` и `фото-работ/`: исходники клиента, не входят в Docker image и не раздаются сервером.
- `docs/architecture.md`: модель данных, границы этапа и план следующих интеграций.

Существующий Vercel-preview продолжает публиковать `wireframe/`. Не менять его root directory на корень репозитория. Push в Git не разворачивает локальный Compose на сервере клиента.

## Кабинет и начальные данные

Откройте http://localhost:8000/cabinet/. На этом checkout создан локальный редактор `vlico`; данные входа находятся в игнорируемом `.local-access.txt`. В других окружениях добавьте VLICO_EDITOR_PASSWORD в приватный `.env`, пересоздайте web и выполните:

```powershell
docker compose exec web python manage.py create_editor --username vlico
```

Команда не меняет существующий аккаунт и не печатает пароль. Смена пароля: `docker compose exec web python manage.py changepassword vlico`. Начальные доступы не предназначены для переноса в production без смены.

Работа редактора: добавьте проект → сохраните основные сведения → загрузите фото → выберите обложку и раздел результата/монтажа → заполните подписи → откройте предпросмотр → подтвердите проверку сведений → опубликуйте. Изменение контента опубликованного проекта становится видно сразу после сохранения. Снятие с публикации немедленно скрывает страницу и фотографии от гостей. Архив сохраняет материалы и позволяет восстановить черновик.

Публичный каталог: http://localhost:8000/projects/. На главную попадают только опубликованные проекты с включённым полем «Показывать на главной». Тарифы и заявки пока не редактируются.

`python manage.py seed_portfolio` создаёт восемь подготовленных черновиков и шесть направлений услуг без публикации и перезаписи существующих данных. Для импорта фотографий используется `--source-root` с доступной контейнеру папкой исходников, смонтированной read-only. Источники не нужно включать в Docker image. В текущую локальную БД фото уже импортированы. Реестр материалов: `docs/portfolio-materials.md`. Не все черновики подтверждены как отдельные объекты.

Плейсхолдеры недостающих данных отображаются в полях кабинета и защищённом предпросмотре; внутренние заметки не публикуются. Общий список работ и sitemap обновляются без деплоя.
