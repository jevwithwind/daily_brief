from typing import List
from models import Article
from thefuzz import fuzz


def deduplicate_articles(articles: List[Article], similarity_threshold: float = 0.85) -> List[Article]:
    """
    Remove duplicate articles based on URL and fuzzy title matching.
    Two articles are considered duplicates if:
    1. They have the same URL, OR
    2. Their titles are very similar (above similarity_threshold)
    """
    unique_articles = []
    seen_urls = set()
    seen_titles = []
    
    for article in articles:
        # Check for URL duplicates
        if article.url in seen_urls:
            continue
        
        # Check for title similarity
        is_duplicate = False
        for seen_title in seen_titles:
            similarity = fuzz.ratio(article.title.lower(), seen_title.lower())
            if similarity >= similarity_threshold * 100:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_articles.append(article)
            seen_urls.add(article.url)
            seen_titles.append(article.title)
    
    return unique_articles