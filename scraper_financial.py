from bs4 import BeautifulSoup
import requests
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.utils import get_stop_words

# Function to summarize a long article using Sumy
def summarize_article_sumy(content, max_sentences=3):
    try:
        # Create a PlaintextParser object from the article content
        parser = PlaintextParser.from_string(content, Tokenizer("english"))
        summarizer = LsaSummarizer()
        summarizer.stop_words = get_stop_words("english")

        # Generate a summary with the specified number of sentences
        summary = summarizer(parser.document, max_sentences)
        return " ".join(str(sentence) for sentence in summary) or "Summary not available."
    except Exception as e:
        print(f"Error summarizing article: {e}")
        return "Summary not available."

# Function to fetch headlines from Financial Express
def fetch_financial_express_headlines(url, limit=5):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        headlines = []

        articles = soup.find_all('article', id=True, limit=limit)
        for article in articles:
            entry_wrapper = article.find('div', class_='entry-wrapper')
            headline_text = headline_url = headline_time = 'Not available'

            if entry_wrapper:
                entry_title_div = entry_wrapper.find('div', class_='entry-title')
                headline_tag = entry_title_div.find('a') if entry_title_div else None
                headline_text = headline_tag.get_text(strip=True) if headline_tag else 'No headline available'
                headline_url = headline_tag['href'] if headline_tag else 'No URL available'

                entry_meta = entry_wrapper.find('div', class_='entry-meta')
                if entry_meta:
                    time_tag = entry_meta.find('time', class_='entry-date published')
                    headline_time = time_tag.get_text(strip=True) if time_tag else 'No time available'

            headlines.append({
                'headline': headline_text,
                'time': headline_time,
                'url': headline_url
            })

        return headlines
    except Exception as e:
        print(f"Error fetching headlines: {str(e)}")
        return []

# Function to fetch article content
def fetch_article_content(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        article_content = 'Content not available'
        article_section = soup.find('div', class_='article-section')
        if article_section:
            content_div = article_section.find('div', class_='post-content wp-block-post-content mb-4')
            if content_div:
                pcl_container = content_div.find('div', class_='pcl-container')
                if pcl_container:
                    paragraphs = pcl_container.find_all('p')
                    article_content = ' '.join([para.get_text() for para in paragraphs])

        return article_content
    except Exception as e:
        print(f"Error fetching article content: {str(e)}")
        return 'Error fetching article content'

# Function to scrape economy news
def scrape_economy_news():
    url = 'https://www.financialexpress.com/about/economy/'

    try:
        headlines = fetch_financial_express_headlines(url)

        if not headlines:
            print("No headlines found.")
            return

        for idx, headline_info in enumerate(headlines, 1):
            print(f"\n📰 Headline {idx}: {headline_info['headline']}")
            print(f"⏰ Published: {headline_info['time']}")
            print(f"Link: {headline_info['url']}")

            article_content = fetch_article_content(headline_info['url'])

            if article_content.startswith("Error"):
                print(f"Error fetching article content for headline {idx}.")
                continue

            summary = summarize_article_sumy(article_content)
            if summary:
                print(f"Summary: {summary}")
            else:
                print("Failed to generate a valid summary.")

    except Exception as e:
        print(f"Error during scraping: {str(e)}")

if __name__ == "__main__":
    scrape_economy_news()




