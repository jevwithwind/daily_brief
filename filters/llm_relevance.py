from typing import List, Optional
from models import Article, TopicConfig, CategoryConfig
from utils.llm_client import LLMClient
import logging

logger = logging.getLogger(__name__)


def filter_by_llm_relevance(articles: List[Article], topic_config: TopicConfig, category_config: CategoryConfig, llm_client: LLMClient) -> List[Article]:
    """
    Filter articles based on LLM relevance scoring.
    Each article gets a relevance score from the LLM, and only articles above the threshold are returned.
    If LLM call fails, fall back to keyword-only filtering (return all articles).
    """
    filtered_articles = []
    
    # Get broad keywords if they exist, otherwise use empty string
    broad_keywords_str = ", ".join(getattr(topic_config, 'keywords_broad', []) or [])
    topic_keywords_str = ", ".join(topic_config.keywords)
    
    for article in articles:
        try:
            # Get relevance score from LLM with enhanced context
            result = llm_client.get_relevance_score(
                article_title=article.title,
                article_summary=article.summary,
                topic_name=topic_config.name,
                category_name=category_config.name,
                topic_keywords=topic_keywords_str,
                topic_broad_keywords=broad_keywords_str,
                language=topic_config.language
            )
            
            if result and 'score' in result:
                article.relevance_score = result['score']
                article.relevance_reason = result.get('reason', '')
                
                # Only include articles that meet the threshold
                if result['score'] >= topic_config.llm_relevance_threshold:
                    filtered_articles.append(article)
                else:
                    logger.debug(f"Article '{article.title}' scored {result['score']} (threshold: {topic_config.llm_relevance_threshold}), excluding")
            else:
                logger.warning(f"Failed to get relevance score for article: {article.title}")
                # If LLM call fails, fall back to including the article (keyword-only filtering)
                # This ensures we still get content even if LLM is unavailable
                filtered_articles.append(article)
                
        except Exception as e:
            logger.error(f"Error processing LLM relevance for article '{article.title}': {str(e)}")
            # If LLM call fails, fall back to including the article (keyword-only filtering)
            filtered_articles.append(article)
    
    return filtered_articles