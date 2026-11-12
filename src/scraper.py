
from __future__ import annotations

import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DATA_DIR / "prices.db"
PRODUCTS_CSV = DATA_DIR / "products.csv"
CHANGES_CSV = DATA_DIR / "price_changes.csv"

HEADERS = {
    "User-Agent": "StudentPriceTracker/1.0 (educational project)"
}

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


def get_soup(session: requests.Session, url: str) -> BeautifulSoup:
    """Download a page and return its parsed HTML."""
    response = session.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def parse_book_cards(soup: BeautifulSoup, page_url: str) -> list[dict]:
    """Extract product fields from all book cards on one catalog page."""
    books = []

    for card in soup.select("article.product_pod"):
        title_link = card.select_one("h3 a")
        price_element = card.select_one(".price_color")
        availability_element = card.select_one(".availability")
        rating_element = card.select_one("p.star-rating")

        if not all([
            title_link,
            price_element,
            availability_element,
            rating_element,
        ]):
            continue

        relative_link = title_link.get("href", "")

        rating_class = next(
            (
                name
                for name in rating_element.get("class", [])
                if name in RATING_MAP
            ),
            None,
        )

        # Extract the numeric price, even if the currency symbol is misencoded.
        price_text = price_element.get_text(strip=True)
        price_match = re.search(r"\d+(?:\.\d+)?", price_text)

        if not price_match:
            raise ValueError(f"Не удалось распознать цену: {price_text!r}")

        price_gbp = float(price_match.group())

        books.append({
            "title": title_link.get("title") or title_link.get_text(strip=True),
            "price_gbp": price_gbp,
            "rating": RATING_MAP.get(rating_class, 0),
            "availability": " ".join(availability_element.stripped_strings),
            "url": urljoin(page_url, relative_link),
        })

    return books


def scrape_catalog() -> pd.DataFrame:
    """Follow the Next link until the catalog has no more pages."""
    all_books = []
    page_url = BASE_URL
    page_number = 1

    with requests.Session() as session:
        while page_url:
            print(f"Загружаю страницу {page_number}: {page_url}")

            soup = get_soup(session, page_url)
            books = parse_book_cards(soup, page_url)
            all_books.extend(books)

            next_link = soup.select_one("li.next a")
            page_url = (
                urljoin(page_url, next_link["href"])
                if next_link
                else None
            )
            page_number += 1

            if page_url:
                time.sleep(1)

    if not all_books:
        raise RuntimeError(
            "Не удалось найти товары. Проверьте доступность сайта и HTML."
        )

    df = pd.DataFrame(all_books)
    df = df.drop_duplicates(subset=["url"]).reset_index(drop=True)

    return df


def init_database(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            title TEXT NOT NULL,
            price_gbp REAL NOT NULL,
            rating INTEGER,
            availability TEXT,
            observed_at TEXT NOT NULL
        )
    """)

    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_history_url "
        "ON price_history(url)"
    )

    connection.commit()


def save_and_compare(df: pd.DataFrame) -> None:
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with sqlite3.connect(DB_PATH) as connection:
        init_database(connection)

        # Get the previous price before inserting this run.
        previous = pd.read_sql_query("""
            SELECT h.url, h.price_gbp AS previous_price
            FROM price_history h
            INNER JOIN (
                SELECT url, MAX(id) AS latest_id
                FROM price_history
                GROUP BY url
            ) latest ON h.id = latest.latest_id
        """, connection)

        current = df.copy()
        current["observed_at"] = observed_at

        current.to_sql(
            "price_history",
            connection,
            if_exists="append",
            index=False,
            method="multi",
        )

        if previous.empty:
            changes = pd.DataFrame(columns=[
                "title",
                "previous_price",
                "current_price",
                "change_gbp",
                "url",
            ])
        else:
            changes = current.merge(previous, on="url", how="inner")

            changes = changes[
                changes["price_gbp"] != changes["previous_price"]
            ].copy()

            changes = changes.rename(
                columns={"price_gbp": "current_price"}
            )

            changes["change_gbp"] = (
                changes["current_price"] - changes["previous_price"]
            )

            changes = changes[[
                "title",
                "previous_price",
                "current_price",
                "change_gbp",
                "url",
            ]]

    df.to_csv(PRODUCTS_CSV, index=False, encoding="utf-8-sig")
    changes.to_csv(CHANGES_CSV, index=False, encoding="utf-8-sig")

    print(f"Товаров собрано: {len(df)}")
    print(f"Изменений цены найдено: {len(changes)}")
    print(f"CSV с товарами: {PRODUCTS_CSV}")
    print(f"CSV с изменениями: {CHANGES_CSV}")
    print(f"История цен: {DB_PATH}")


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        products = scrape_catalog()
        save_and_compare(products)
        return 0

    except requests.RequestException as error:
        print(f"Ошибка HTTP-запроса: {error}", file=sys.stderr)
        return 1

    except Exception as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
