import re
import nltk
nltk.download('stopwords', quiet=True)

def clean_text(text: str) -> str:
    """Clean raw legal text."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters except legal punctuation
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\'\"]', '', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text

def normalize_text(text: str) -> str:
    """Normalize text for consistency."""
    text = clean_text(text)
    # Lowercase only for indexing purposes (keep original for display)
    return text