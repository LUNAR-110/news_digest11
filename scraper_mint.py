import requests
from bs4 import BeautifulSoup
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from collections import Counter
import nltk

# Ensure you have downloaded the necessary NLTK data files
nltk.download('punkt')
nltk.download('stopwords')

class MintScraper:
    def __init__(self):
        # Define the headers to mimic a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _scrape_generic(self, url, container_tag, container_class, title_tag, link_tag, prefix=""):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
            soup = BeautifulSoup(response.content, 'html.parser')

            articles = []
            containers = soup.find_all(container_tag, class_=container_class)
            for container in containers:
                title_element = container.find(title_tag)
                link_element = title_element.find(link_tag) if title_element else None

                title = title_element.get_text(strip=True) if title_element else "No title available"
                link = prefix + link_element['href'] if link_element and 'href' in link_element.attrs else "No URL available"
                published_time = container.find('time')['datetime'] if container.find('time') else 'Not available'

                articles.append({"title": title, "link": link, "time": published_time})

            return articles
        except Exception as e:
            print(f"Error during scraping: {e}")
            return []

    def fetch_article_content(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            paragraphs = soup.find_all('p')
            content = " ".join([p.get_text() for p in paragraphs])
            return content
        except Exception as e:
            print(f"Error fetching article content: {e}")
            return "Content not available"

    def summarize_article(self, content, sentence_count=3):
        # Tokenize the content into sentences
        sentences = sent_tokenize(content)

        # Tokenize the content into words and remove stopwords
        stop_words = set(stopwords.words("english"))
        words = word_tokenize(content.lower())
        words = [word for word in words if word.isalnum() and word not in stop_words]

        # Count the frequency of each word
        word_freq = Counter(words)

        # Score each sentence based on the frequency of the words it contains
        sentence_scores = {}
        for sentence in sentences:
            for word in word_tokenize(sentence.lower()):
                if word in word_freq:
                    if sentence not in sentence_scores:
                        sentence_scores[sentence] = word_freq[word]
                    else:
                        sentence_scores[sentence] += word_freq[word]

        # Get the top 'sentence_count' sentences
        summarized_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:sentence_count]
        return ' '.join(summarized_sentences)

    def scrape_mint(self):
        url = "https://www.livemint.com/latest-news"
        return self._scrape_generic(url, "div", "listingNew", "h2", "a", prefix="https://www.livemint.com")

if __name__ == "__main__":
    print("Fetching latest news from Mint...")
    mint_scraper = MintScraper()
    articles = mint_scraper.scrape_mint()

    # Limit to the first 5 articles
    articles = articles[:5]

    if articles:
        for idx, article in enumerate(articles, 1):
            print(f"\n📰 Headline {idx}: {article['title']}")
           
            print(f"Link: {article['link']}")

            # Fetch the content of the article
            article_content = mint_scraper.fetch_article_content(article['link'])

            # Summarize the article content
            summary = mint_scraper.summarize_article(article_content)

            print(f"Summary: {summary}")
    else:
        print("No articles found.")


