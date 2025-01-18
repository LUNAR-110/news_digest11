from bs4 import BeautifulSoup
import requests
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.utils import get_stop_words
import re

# Function to clean article content
def clean_article_content(content):
    """
    Removes unwanted numerical patterns, special characters, and extra whitespace from the content.
    """
    content = re.sub(r'[0-9]+(?:\.[0-9]+)?', '', content)  # Remove numbers
    content = re.sub(r'[^\w\s.,;:!?]', '', content)  # Remove special characters except punctuation
    content = re.sub(r'\s+', ' ', content)  # Remove extra whitespace
    return content.strip()

# Function to summarize a long article using Sumy
def summarize_article_sumy(content, max_sentences=3):
    """
    Summarizes the content using the LSA (Latent Semantic Analysis) summarizer from Sumy.
    """
    parser = PlaintextParser.from_string(content, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summarizer.stop_words = get_stop_words("english")
    summary = summarizer(parser.document, max_sentences)
    return " ".join(str(sentence) for sentence in summary)

# Function to fetch headlines and links from The Hindu BusinessLine
def fetch_thehindu_headlines(url, limit=5):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        headlines = []

        # Find all headline elements (adjust the selector to match the website)
        articles = soup.find_all('a', class_='element', limit=limit)  # Example class; adjust as necessary

        for article in articles:
            headline_text = article.get_text(strip=True)
            headline_url = article['href']
            if not headline_url.startswith('http'):
                headline_url = f"https://www.thehindubusinessline.com{headline_url}"
            headlines.append({'headline': headline_text, 'url': headline_url})

        return headlines

    except Exception as e:
        print(f"Error fetching headlines: {str(e)}")
        return []

# Function to fetch article content and publication time
def fetch_article_details(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract article content
        paragraphs = soup.find_all('p')
        article_content = " ".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

        # Clean content for summarization
        article_content = clean_article_content(article_content)

        # Extract publication time (adjust the selector as necessary)
        time_tag = soup.find('time')  # Example: time element
        published_time = time_tag.get_text(strip=True) if time_tag else "No time available"

        return article_content, published_time

    except Exception as e:
        print(f"Error fetching article details: {str(e)}")
        return None, "No time available"

# Function to scrape economy news
def scrape_economy_news():
    base_url = 'https://www.thehindubusinessline.com/economy/'

    try:
        # Fetch headlines from The Hindu BusinessLine
        headlines = fetch_thehindu_headlines(base_url, limit=5)

        if not headlines:
            print("No headlines found.")
            return

        # Process each headline and fetch details
        for idx, headline_info in enumerate(headlines, 1):
            print(f"\n📰 Headline {idx}: {headline_info['headline']}")
            print(f"🔗 Link: {headline_info['url']}")

            # Fetch article content and publication time
            article_content, published_time = fetch_article_details(headline_info['url'])

            # If no content is available, skip to the next headline
            if not article_content:
                print("Error fetching article content.")
                continue

            # Summarize the article content using Sumy
            summary = summarize_article_sumy(article_content)
            print(f"⏰ Published: {published_time}")
            print(f"🔍 Summary: {summary}")

    except Exception as e:
        print(f"Error during scraping: {str(e)}")

if __name__ == "__main__":
    scrape_economy_news()




