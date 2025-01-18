
from flask import Flask, render_template, jsonify
from bs4 import BeautifulSoup
import requests
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.utils import get_stop_words
import re
import nltk
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()

# Update the app.run() at the bottom
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



# Ensure you have downloaded the necessary NLTK data files
nltk.download('punkt')
nltk.download('stopwords')

app = Flask(__name__)

# Importing the Financial Express scraper functions
from scraper_financial import fetch_financial_express_headlines, fetch_article_content, summarize_article_sumy

# Importing the EconomicScraper class
from scraper_economic import EconomicScraper

# Integrating News18Scraper
from scraper_news18 import News18Scraper

# Function to clean article content
def clean_article_content(content):
    content = re.sub(r'[0-9]+(?:\.[0-9]+)?', '', content)  # Remove numbers
    content = re.sub(r'[^\w\s.,;:!?]', '', content)  # Remove special characters except punctuation
    content = re.sub(r'\s+', ' ', content)  # Remove extra whitespace
    return content.strip()

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

        articles = soup.find_all('a', class_='element', limit=limit)  # Adjust the class as necessary

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
        paragraphs = soup.find_all('p')
        article_content = " ".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        article_content = clean_article_content(article_content)

        time_tag = soup.find('time')  # Example: time element
        published_time = time_tag.get_text(strip=True) if time_tag else "No time available"

        return article_content, published_time

    except Exception as e:
        print(f"Error fetching article details: {str(e)}")
        return None, "No time available"

# Mint Scraper
def fetch_mint_headlines(url="https://www.livemint.com/latest-news", limit=5):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        headlines = []

        containers = soup.find_all('div', class_='listingNew', limit=limit)
        for container in containers:
            title_element = container.find('h2')
            link_element = title_element.find('a') if title_element else None

            title = title_element.get_text(strip=True) if title_element else "No title available"
            link = f"https://www.livemint.com{link_element['href']}" if link_element and 'href' in link_element.attrs else "No URL available"
            published_time = container.find('time')['datetime'] if container.find('time') else "Not available"

            headlines.append({'headline': title, 'url': link, 'time': published_time})

        return headlines
    except Exception as e:
        print(f"Error fetching Mint headlines: {e}")
        return []

# Home route
@app.route('/')
def home():
    return render_template('index.html')

# Route to fetch news from The Hindu BusinessLine
@app.route('/fetch-hindu-news', methods=['GET'])
def fetch_hindu_news():
    base_url = 'https://www.thehindubusinessline.com/economy/'
    headlines = fetch_thehindu_headlines(base_url, limit=5)

    if not headlines:
        return jsonify({'error': 'No headlines found for The Hindu BusinessLine.'}), 500

    news_data = []

    for headline_info in headlines:
        article_content, published_time = fetch_article_details(headline_info['url'])
        if not article_content:
            continue
        summary = summarize_article_sumy(article_content)
        news_data.append({
            'headline': headline_info['headline'],
            'url': headline_info['url'],
            'source': 'The Hindu BusinessLine',
            'summary': summary
        })

    return jsonify(news_data)

# Route to fetch news from Mint
@app.route('/fetch-mint-news', methods=['GET'])
def fetch_mint_news():
    headlines = fetch_mint_headlines(limit=5)

    if not headlines:
        return jsonify({'error': 'No headlines found for Mint.'}), 500

    news_data = []

    for headline_info in headlines:
        article_content = fetch_article_details(headline_info['url'])[0]
        if not article_content:
            continue
        summary = summarize_article_sumy(article_content)
        news_data.append({
            'headline': headline_info['headline'],
            'url': headline_info['url'],
            'source': 'Mint',
            'summary': summary
        })

    return jsonify(news_data)

# Route to fetch news from Financial Express
@app.route('/fetch-financial-news', methods=['GET'])
def fetch_financial_news():
    base_url = 'https://www.financialexpress.com/about/economy/'
    headlines = fetch_financial_express_headlines(base_url, limit=5)

    if not headlines:
        return jsonify({'error': 'No headlines found for Financial Express.'}), 500

    news_data = []

    for headline_info in headlines:
        article_content = fetch_article_content(headline_info['url'])
        if article_content.startswith("Error"):
            continue
        summary = summarize_article_sumy(article_content)
        news_data.append({
            'headline': headline_info['headline'],
            'url': headline_info['url'],
            'source': 'Financial Express',
            'summary': summary
        })

    return jsonify(news_data)

# Route to fetch news from News18
@app.route('/fetch-news18-news', methods=['GET'])
def fetch_news18_news():
    scraper = News18Scraper()
    news_data = []

    for category, path in scraper.categories.items():
        print(f"Scraping category: {category}")
        links = scraper.get_article_links(scraper.base_url + path, category, limit=5)

        for link in links:
            article_data = scraper.extract_article_data(link)
            if article_data:
                news_data.append({
                    'headline': article_data['headline'],
                    'url': article_data['link'],
                    'source': 'News18',
                    'summary': article_data['summary']
                })

    return jsonify(news_data)

# Route to fetch economic news
@app.route('/fetch-economic-news', methods=['GET'])
def fetch_economic_news():
    scraper = EconomicScraper()
    headlines = scraper.fetch_headlines()

    if not headlines:
        return jsonify({'error': 'No headlines found for Economic Times.'}), 500

    news_data = []

    # Use ThreadPoolExecutor for concurrent fetching of articles
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_article = {executor.submit(scraper.fetch_article_details, article['url']): article for article in headlines}

        for future in concurrent.futures.as_completed(future_to_article):
            article = future_to_article[future]
            try:
                summary = future.result()
                if summary.startswith("Error"):
                    continue

                news_data.append({
                    'headline': article['headline'],
                    'url': article['url'],
                    'source': 'Economic Times',
                    'summary': summary
                })
            except Exception as e:
                print(f"Error fetching article details for {article['headline']}: {e}")

    return jsonify(news_data)



if __name__ == "__main__":
    app.run(debug=True)

