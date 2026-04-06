import feedparser
from typing import List
import logging
from urllib.parse import quote
from datetime import datetime, timezone
from .base import BaseCollector
from models import Article, SourceConfig

logger = logging.getLogger(__name__)


class PrTimesCollector(BaseCollector):
    """Collector for PR Times Japan press releases via Google News RSS"""
    
    def collect(self, source_config: SourceConfig) -> List[Article]:
        """Collect articles from PR Times based on company keywords using Google News RSS"""
        articles = []
        
        if not source_config.company_keywords:
            logger.error(f"No company keywords provided for PR Times source: {source_config.name}")
            return articles
        
        # Build a Google News RSS query for PR Times
        # Combine all keywords into a single query
        keyword_query = ' OR '.join([f'site:prtimes.jp {kw}' for kw in source_config.company_keywords])
        
        try:
            # Construct Google News RSS URL for PR Times
            encoded_query = quote(keyword_query)
            google_news_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"
            
            # Parse the Google News RSS feed
            feed = feedparser.parse(google_news_url)
            
            if feed.bozo:
                logger.warning(f"Feed parsing issue for {source_config.name}: {feed.bozo_exception}")
            
            for entry in feed.entries[:20]:  # Limit to 20 articles
                try:
                    # Extract publication date
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
                        content=summary
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.error(f"Error processing entry from {source_config.name}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching Google News for PR Times: {str(e)}")
        
        logger.info(f"Collected {len(articles)} articles from PR Times (via Google News) for source: {source_config.name}")
        return articles