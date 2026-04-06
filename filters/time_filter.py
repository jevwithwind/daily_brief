from typing import List
from datetime import datetime, timedelta, timezone
from models import Article


def filter_by_time(articles: List[Article], hours: int = 48) -> List[Article]:
    """
    Filter articles to only include those published within the last 'hours' hours.
    Default is 48 hours to account for weekend gaps and slower updating feeds.
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    filtered_articles = [
        article for article in articles
        if article.published_at >= cutoff_time
    ]
    
    return filtered_articles