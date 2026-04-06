from typing import List, Dict
from models import Article, TopicConfig
from utils.llm_client import LLMClient
import logging

logger = logging.getLogger(__name__)


class Summarizer:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    def summarize_article(self, article: Article) -> str:
        """Generate a summary for a single article"""
        if article.content:
            summary = self.llm_client.generate_summary(
                article_title=article.title,
                article_content=article.content,
                language=article.language
            )
            if summary:
                return summary
        
        # Fallback to using summary if content is not available
        summary = self.llm_client.generate_summary(
            article_title=article.title,
            article_content=article.summary,
            language=article.language
        )
        return summary if summary else article.summary
    
    def summarize_topic(self, articles: List[Article], topic_config: TopicConfig) -> str:
        """Generate an executive summary for a topic"""
        if not articles:
            return ""
        
        summary = self.llm_client.generate_executive_summary(
            articles=articles,
            topic_name=topic_config.name,
            language=topic_config.language
        )
        return summary if summary else f"Summary for {topic_config.name} could not be generated."
    
    def process_articles_with_summaries(self, articles: List[Article]) -> List[Article]:
        """Process a list of articles and add summaries to each"""
        processed_articles = []
        
        for article in articles:
            try:
                article.summary = self.summarize_article(article)
                processed_articles.append(article)
            except Exception as e:
                logger.error(f"Error summarizing article '{article.title}': {str(e)}")
                # Still add the article even if summarization failed
                processed_articles.append(article)
        
        return processed_articles