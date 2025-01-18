
import logging
from datetime import datetime
import sqlite3
from bs4 import BeautifulSoup
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor

class EconomicScraper:
    def __init__(self):
        self.base_url = 'https://economictimes.indiatimes.com/news/economy?from=mdr'
        self.db_path = "newsapp.db"
        self.setup_database()

    def setup_database(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""CREATE TABLE IF NOT EXISTS economic_table (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    Headline TEXT UNIQUE NOT NULL,
                                    Time TEXT NOT NULL,
                                    Link TEXT NOT NULL,
                                    Summary TEXT,
                                    Source TEXT NOT NULL);""")
                logging.info("Database and table setup complete.")
        except Exception as e:
            logging.error(f"Error setting up database: {e}")

    def delete_oldest_record(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""DELETE FROM economic_table 
                                  WHERE id = (SELECT id FROM economic_table ORDER BY datetime(Time) ASC LIMIT 1);""")
                conn.commit()
                logging.info("Oldest record deleted to maintain 5 records.")
        except Exception as e:
            logging.error(f"Error deleting oldest record: {e}")

    def is_headline_in_database(self, headline):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM economic_table WHERE Headline = ?", (headline,))
                return cursor.fetchone() is not None
        except Exception as e:
            logging.error(f"Error checking headline in database: {e}")
            return False

    def fetch_all_database_records(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM economic_table ORDER BY datetime(Time) DESC;")
                records = cursor.fetchall()
                return records
        except Exception as e:
            logging.error(f"Error fetching database records: {e}")
            return []

    def store_to_database(self, headline, time, link, summary, source):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""INSERT INTO economic_table (Headline, Time, Link, Summary, Source)
                                  VALUES (?, ?, ?, ?, ?);""", (headline, time, link, summary, source))
                conn.commit()
                logging.info(f"Stored in database: {headline}")

                cursor.execute("SELECT COUNT(*) FROM economic_table;")
                record_count = cursor.fetchone()[0]
                if record_count > 5:
                    self.delete_oldest_record()
        except sqlite3.IntegrityError:
            logging.info(f"Duplicate headline skipped: {headline}")
        except Exception as e:
            logging.error(f"Error storing to database: {e}")

    def fetch_article_details(self, article_url):
        logging.info(f"Fetching article details from: {article_url}")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(article_url, timeout=12000)
                page_content = page.content()
                browser.close()

            soup = BeautifulSoup(page_content, 'html.parser')

            article_body = soup.find("div", class_="artText medium")
            if not article_body:
                article_body = soup.find("div", class_="article-body") or soup.find("div", class_="content")
            article_text = article_body.get_text(separator=" ", strip=True) if article_body else "Article body not found."

            summary = self.summarize_article(article_text)

            return summary
        except Exception as e:
            logging.error(f"Error fetching article details: {e}")
            return "Error fetching article details."

    def summarize_article(self, content):
        try:
            parser = PlaintextParser.from_string(content, Tokenizer("english"))
            summarizer = LexRankSummarizer()
            summary_sentences = summarizer(parser.document, 3)
            return " ".join(str(sentence) for sentence in summary_sentences)
        except Exception as e:
            logging.error(f"Error in summarization: {e}")
            return "Error in summarization."

    def fetch_headlines(self, featured_limit=2, top_limit=3):
        logging.info(f"Fetching headlines from: {self.base_url}")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(self.base_url, timeout=60000)
                page_content = page.content()
                browser.close()

            soup = BeautifulSoup(page_content, 'html.parser')

            featured_headlines = []
            featured_divs = soup.find_all('div', class_='featured')
            for div in featured_divs[:featured_limit]:
                link = div.find('a')
                if link and link.get('href'):
                    headline_text = link.get_text(strip=True)
                    headline_url = link['href']
                    if not headline_url.startswith('http'):
                        headline_url = f"https://economictimes.indiatimes.com{headline_url}"
                    time_tag = div.find('time', class_='date-format')
                    published_time = time_tag['data-time'] if time_tag else datetime.now().isoformat()
                    featured_headlines.append({
                        'headline': headline_text,
                        'url': headline_url,
                        'time': published_time,
                        'source': 'Economic Times'
                    })

            top_headlines = []
            ul_tag = soup.find('ul', class_='list1')
            if ul_tag:
                for li in ul_tag.find_all('li')[:top_limit]:
                    link = li.find('a')
                    if link and link.get('href'):
                        headline_text = link.get_text(strip=True)
                        headline_url = link['href']
                        if not headline_url.startswith('http'):
                            headline_url = f"https://economictimes.indiatimes.com{headline_url}"
                        time_tag = li.find('time', class_='date-format')
                        published_time = time_tag['data-time'] if time_tag else datetime.now().isoformat()
                        top_headlines.append({
                            'headline': headline_text,
                            'url': headline_url,
                            'time': published_time,
                            'source': 'Economic Times'
                        })

            return featured_headlines + top_headlines

        except Exception as e:
            logging.error(f"Error fetching headlines: {e}")
            return []

    def scrape_economy_news(self):
        """Scrape economy news and store in the database."""
        headlines = self.fetch_headlines()

        with ThreadPoolExecutor() as executor:
            futures = []
            for article in headlines:
                if self.is_headline_in_database(article['headline']):
                    logging.info("Duplicate headline found. Stopping further scraping.")
                    break
                
                future = executor.submit(self.fetch_article_details, article['url'])
                futures.append((future, article))

            for future, article in futures:
                try:
                    summary = future.result()
                    self.store_to_database(
                        article['headline'],
                        article['time'],
                        article['url'],
                        summary,
                        article['source']
                    )
                except Exception as e:
                    logging.error(f"Error processing article {article['headline']}: {e}")

        # Print all database data
        records = self.fetch_all_database_records()
        for record in records:
            print(record)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scraper = EconomicScraper()
    scraper.scrape_economy_news()













