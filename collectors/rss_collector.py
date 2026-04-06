import feedparser
import requests
from datetime import datetime, timezone
from typing import List
import logging
from .base import BaseCollector
from models import Article, SourceConfig

logger = logging.getLogger(__name__)


class RSSCollector(BaseCollector):
    """Collector for RSS and Atom feeds"""
    
    def collect(self, source_config: SourceConfig) -> List[Article]:
        """Collect articles from RSS/Atom feed"""
        articles = []
        
        try:
            # Parse the RSS feed
            feed = feedparser.parse(source_config.url)
            
            if feed.bozo:
                logger.warning(f"Feed parsing issue for {source_config.name}: {feed.bozo_exception}")
            
            for entry in feed.entries:
                try:
                    # Extract publication date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                    else:
                        pub_date = datetime.now(timezone.utc)
                    
                    # Extract content/summary
                    summary = getattr(entry, 'summary', '')
                    if not summary and hasattr(entry, 'content'):
                        summary = entry.content[0].value if entry.content else ''
                    
                    # Create article object
                    article = Article(
                        title=getattr(entry, 'title', ''),
                        summary=summary,
                        url=getattr(entry, 'link', ''),
                        source=source_config.name,
                        published_at=pub_date,
                        content=getattr(entry, 'content', [{}])[0].get('value', '') if hasattr(entry, 'content') and entry.content else summary
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.error(f"Error processing entry from {source_config.name}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching RSS feed {source_config.url}: {str(e)}")
        
        logger.info(f"Collected {len(articles)} articles from {source_config.name}")
        return articles