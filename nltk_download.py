
import nltk

def download_nltk_data():
    required_packages = [
        'punkt',
        'stopwords',
        'averaged_perceptron_tagger'
    ]
    
    for package in required_packages:
        try:
            nltk.download(package)
            print(f"Successfully downloaded {package}")
        except Exception as e:
            print(f"Error downloading {package}: {str(e)}")

if __name__ == "__main__":

