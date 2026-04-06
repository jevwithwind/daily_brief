from typing import List
from models import Article, TopicConfig


def filter_by_keywords(articles: List[Article], topic_config: TopicConfig) -> List[Article]:
    strict_keywords = topic_config.keywords
    broad_keywords = getattr(topic_config, 'keywords_broad', []) or []
    filtered = []

    for article in articles:
        text = f"{article.title} {article.summary}".lower()

        strict_match = any(kw.lower() in text for kw in strict_keywords)

        broad_count = sum(1 for kw in broad_keywords if kw.lower() in text)
        broad_match = broad_count >= 2

        if strict_match or broad_match:
            filtered.append(article)

    return filtered