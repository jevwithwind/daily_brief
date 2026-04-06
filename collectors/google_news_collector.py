import feedparser
from typing import List
import logging
from urllib.parse import quote
from .base import BaseCollector
from models import Article, SourceConfig

logger = logging.getLogger(__name__)


class GoogleNewsCollector(BaseCollector):
    """Collector for Google News RSS feeds"""
    
    def collect(self, source_config: SourceConfig) -> List[Article]:
        """Collect articles from Google News using custom queries"""
        articles = []
        
        if not source_config.query:
            logger.error(f"No query provided for Google News source: {source_config.name}")
            return articles
        
        # Construct Google News RSS URL
        encoded_query = quote(source_config.query)
        google_news_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        
        # For Japanese queries, we'll adjust the language settings
        if any('\u3040' <= char <= '\u309f' or '\u30a0' <= char <= '\u30ff' or '\u4e00' <= char <= '\u9faf' for char in source_config.query):
            google_news_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"
        
        try:
            # Parse the Google News RSS feed
            feed = feedparser.parse(google_news_url)
            
            if feed.bozo:
                logger.warning(f"Feed parsing issue for {source_config.name}: {feed.bozo_exception}")
            
            for entry in feed.entries:
                try:
                    # Extract publication date
                    from datetime import datetime, timezone
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    else:
                        pub_date = datetime.now(timezone.utc)
                    
                    # Extract content/summary
                    summary = getattr(entry, 'summary', '')
                    
                    # Create article object
                    article = Article(
                        title=getattr(entry, 'title', ''),
                        summary=summary,
                        url=getattr(entry, 'link', ''),
                        source=source_config.name,
                        published_at=pub_date,
                        content=summary  # Google News usually has good summaries
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.error(f"Error processing entry from {source_config.name}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching Google News feed for query '{source_config.query}': {str(e)}")
        
        logger.info(f"Collected {len(articles)} articles from Google News query: {source_config.query}")
        return articles