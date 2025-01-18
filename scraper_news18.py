import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
import re

class News18Scraper:
    def __init__(self):
        self.base_url = "https://www.news18.com"
        self.categories = {
            "Economy": "/business/economy",
            "Global Economy": "/business/economy/global-economy",
            "Commodities": "/business/markets/commodities",
            "Gold Prices": "/business/markets/commodity/gold-price",
            "Climate Change": "/news/environment/climate-change"
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.min_content_words = 100

    def is_relevant_article(self, url, category):
        """Check if article URL is relevant to the category"""
        if not url:
            return False
            
        category_keywords = {
            "Economy": ['economy', 'gdp', 'inflation', 'economic', 'finance', 'rbi', 'trade'],
            "Global Economy": ['global', 'world', 'international', 'trade', 'forex', 'foreign'],
            "Commodities": ['commodity', 'commodities', 'crude', 'oil', 'metal', 'palm-oil', 'soybean'],
            "Gold Prices": ['gold-price', 'gold-rates', 'silver-price', 'bullion'],
            "Climate Change": ['climate', 'environment', 'carbon', 'emission', 'sustainable']
        }
        
        # Include the category URL path as a relevant keyword
        category_path = self.categories[category].lower()
        keywords = category_keywords.get(category, []) + [category_path.strip('/')]
        
        return any(keyword in url.lower() for keyword in keywords)

    def get_article_links(self, category_url, category_name, limit=5):
        """Extract limited article links from a category page"""
        try:
            response = requests.get(category_url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            article_links = []
            processed_count = 0
            
            # Method 1: Find articles by class
            articles = soup.find_all(['div', 'article'], class_=lambda x: x and any(c in str(x).lower() for c in ['article', 'news-list', 'news_item']))
            
            # Method 2: Find all links
            if not articles:
                articles = soup.find_all('a', href=True)
            
            for article in articles:
                if len(article_links) >= limit:
                    break
                
                # Extract URL based on element type
                url = None
                if article.name == 'a':
                    url = article.get('href', '')
                else:
                    link = article.find('a', href=True)
                    if link:
                        url = link.get('href', '')
                
                if not url:
                    continue
                    
                # Clean and validate URL
                url = url.strip()
                if url.startswith('//'):
                    url = 'https:' + url
                elif url.startswith('/'):
                    url = self.base_url + url
                elif not (url.startswith('http://') or url.startswith('https://')):
                    continue
                
                # Verify it's a news18 URL
                if 'news18.com' not in url:
                    continue
                
                # Check relevance and content
                if self.is_relevant_article(url, category_name):
                    print(f"Checking content for: {url}")
                    if self.has_sufficient_content(url):
                        if url not in article_links:
                            article_links.append(url)
                            print(f"Added valid article: {url}")
                    processed_count += 1
                
                if processed_count > limit * 4:
                    break
            
            print(f"Found {len(article_links)} valid articles with sufficient content")
            return article_links
            
        except Exception as e:
            print(f"Error getting article links: {str(e)}")
            return []

    def has_sufficient_content(self, url):
        """Check if article has sufficient content for summarization"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract content using multiple methods
            content_text = []
            
            # Method 1: Main article content
            content_divs = soup.find_all('div', class_=lambda x: x and any(c in str(x).lower() for c in [
                'article-content', 'story-content', 'content_text', 'article_body',
                'article-txt', 'story_text', 'content-text'
            ]))
            
            # Method 2: Main content area
            if not content_divs:
                content_divs = soup.find_all('div', {'class': ['content_area', 'article_area', 'main-content']})
            
            # Method 3: Article container
            if not content_divs:
                content_divs = soup.find_all('article')
            
            for div in content_divs:
                # Get paragraphs
                paragraphs = div.find_all('p')
                for p in paragraphs:
                    if not p.find(['script', 'style', 'iframe']):
                        text = p.text.strip()
                        if text and len(text) > 20:  # Skip very short paragraphs
                            content_text.append(text)
            
            # If still no content, try getting all paragraphs
            if not content_text:
                for p in soup.find_all('p'):
                    if not p.find(['script', 'style', 'iframe']):
                        text = p.text.strip()
                        if text and len(text) > 20:
                            content_text.append(text)
            
            content = ' '.join(content_text)
            word_count = len(content.split())
            
            print(f"Found {word_count} words in article")
            return word_count >= self.min_content_words
            
        except Exception as e:
            print(f"Error checking content length for {url}: {str(e)}")
            return False

    def extract_article_data(self, article_url):
        """Extract data from a single article"""
        try:
            response = requests.get(article_url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract headline
            headline = None
            headline_elem = soup.find('h1')
            if headline_elem:
                headline = headline_elem.text.strip()
            else:
                # Try alternative methods to find headline
                meta_title = soup.find('meta', property='og:title')
                if meta_title:
                    headline = meta_title.get('content', '').strip()
            
            if not headline:
                return None
            
            # Extract date
            publish_date = "N/A"
            publish_time = "N/A"
            
            # Try multiple date extraction methods
            date_elem = soup.find(['time', 'span'], class_=lambda x: x and any(c in str(x).lower() for c in ['date', 'time', 'published']))
            if date_elem and date_elem.get('datetime'):
                try:
                    dt = datetime.fromisoformat(date_elem['datetime'].replace('Z', '+00:00'))
                    publish_date = dt.strftime('%Y-%m-%d')
                    publish_time = dt.strftime('%H:%M:%S')
                except:
                    pass
            
            if publish_date == "N/A":
                scripts = soup.find_all('script', type='application/ld+json')
                for script in scripts:
                    try:
                        if 'datePublished' in script.string:
                            date_match = re.search(r'"datePublished":"([^"]+)"', script.string)
                            if date_match:
                                date_str = date_match.group(1)
                                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                publish_date = dt.strftime('%Y-%m-%d')
                                publish_time = dt.strftime('%H:%M:%S')
                                break
                    except:
                        continue
            
            # Extract content using the same method as has_sufficient_content
            content_text = []
            content_divs = soup.find_all('div', class_=lambda x: x and any(c in str(x).lower() for c in [
                'article-content', 'story-content', 'content_text', 'article_body',
                'article-txt', 'story_text', 'content-text'
            ]))
            
            if not content_divs:
                content_divs = soup.find_all('div', {'class': ['content_area', 'article_area', 'main-content']})
            
            if not content_divs:
                content_divs = soup.find_all('article')
            
            for div in content_divs:
                paragraphs = div.find_all('p')
                for p in paragraphs:
                    if not p.find(['script', 'style', 'iframe']):
                        text = p.text.strip()
                        if text and len(text) > 20:
                            content_text.append(text)
            
            content = ' '.join(content_text)
            
            if not content or len(content.split()) < self.min_content_words:
                return None
            
            summary = self.generate_summary(content)
            
            return {
                'headline': headline,
                'link': article_url,
                'publish_date': publish_date,
                'publish_time': publish_time,
                'summary': summary
            }
            
        except Exception as e:
            print(f"Error extracting data from {article_url}: {str(e)}")
            return None

    def generate_summary(self, text, sentences_count=3):
        """Generate summary using Sumy"""
        try:
            text = re.sub(r'\s+', ' ', text).strip()
            
            parser = PlaintextParser.from_string(text, Tokenizer("english"))
            stemmer = Stemmer("english")
            summarizer = LsaSummarizer(stemmer)
            summarizer.stop_words = get_stop_words("english")
            
            summary = []
            for sentence in summarizer(parser.document, sentences_count):
                summary.append(str(sentence))
            
            return ' '.join(summary) if summary else "Unable to generate summary"
            
        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            return "Error in summary generation"

    def print_article(self, article_data):
        """Print article data in a formatted way"""
        print("\n" + "="*100)
        print(f"HEADLINE: {article_data['headline']}")
        print(f"LINK: {article_data['link']}")
        print(f"PUBLISHED: {article_data['publish_date']} at {article_data['publish_time']}")
        print("\nSUMMARY:")
        print(article_data['summary'])

    def scrape_articles(self):
        """Main function to scrape articles from each category"""
        for category_name, category_path in self.categories.items():
            print(f"\n\nScraping category: {category_name}")
            print("-" * 50)
            
            category_url = self.base_url + category_path
            article_links = self.get_article_links(category_url, category_name, limit=5)
            
            if not article_links:
                print(f"No valid articles found for category: {category_name}")
                continue
            
            for link in article_links:
                article_data = self.extract_article_data(link)
                if article_data:
                    self.print_article(article_data)
                time.sleep(2)

if __name__ == "__main__":
    print("Starting News18 Article Scraper...")
    print("Scraping articles with sufficient content from each category...")
    scraper = News18Scraper()
    scraper.scrape_articles()