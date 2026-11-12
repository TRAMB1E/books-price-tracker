# Web Scraper — Product Price Tracker

Учебный проект по веб-скрейпингу на Python. Парсер собирает названия и цены книг с сайта
[Books to Scrape](https://books.toscrape.com/) — специального демонстрационного магазина,
созданного для обучения парсингу.

## Что делает проект

- Загружает страницы каталога.
- Извлекает название, цену, рейтинг, наличие и ссылку на товар.
- Переходит по всем страницам каталога (пагинация).
- Сохраняет актуальные данные в `data/products.csv`.
- Записывает каждое наблюдение в SQLite (`data/prices.db`).
- При повторном запуске сравнивает цены с предыдущим запуском и создаёт `data/price_changes.csv`.

## Структура проекта

```text
books-price-tracker/
├── src/
│   └── scraper.py
├── data/
├── .github/
│   └── workflows/
│       └── daily.yml
├── requirements.txt
├── .gitignore
└── README.md
```

## Установка и запуск

Требуется Python 3.10 или новее.

```bash
python -m venv .venv

# Windows:
.venv\\Scripts\\activate

# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
python src/scraper.py
```

После выполнения в папке `data` появятся:
- `products.csv` — полный текущий каталог;
- `price_changes.csv` — сравнение с предыдущим запуском (при первом запуске будет пустым);
- `prices.db` — история цен.

## Как устроен парсер

1. `requests.get()` получает HTML страницы.
2. `BeautifulSoup` разбирает HTML.
3. CSS-селектор `article.product_pod` находит карточки книг.
4. Из карточки извлекаются название, цена, рейтинг, наличие и ссылка.
5. Ссылка `li.next a` используется для перехода на следующую страницу.
6. Pandas сохраняет данные в CSV, SQLite хранит историю наблюдений.

## Автоматический запуск на GitHub

В репозитории откройте **Settings → Actions → General → Workflow permissions** и выберите
**Read and write permissions**. Затем вкладка **Actions** → **Daily price tracker** →
**Run workflow**.

Workflow также запускается ежедневно в 06:00 UTC. GitHub Actions сохраняет обновлённые
CSV и базу данных коммитом в репозиторий.

## Ограничения учебного проекта

Books to Scrape — демонстрационный магазин. Цены и товары вымышленные и не отражают
реальный рынок. Не используйте этот учебный код для обхода ограничений реальных сайтов.
Соблюдайте условия использования и правила доступа каждого сайта.
