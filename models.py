from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


@dataclass
class Article:
    """Represents a news article with all relevant metadata"""
    title: str
    summary: str
    url: str
    source: str
    published_at: datetime
    relevance_score: Optional[float] = None
    relevance_reason: Optional[str] = None
    content: Optional[str] = None  # Full content if available
    tags: Optional[List[str]] = None
    language: str = "en"  # Language code (en, ja, etc.)
    topic_name: Optional[str] = None
    category_name: Optional[str] = None


@dataclass
class SourceConfig:
    """Configuration for a single data source"""
    type: str  # 'rss', 'google_news', 'prtimes'
    name: str
    url: Optional[str] = None
    query: Optional[str] = None
    company_keywords: Optional[List[str]] = None


@dataclass
class TopicConfig:
    """Configuration for a single topic within a category"""
    name: str
    tags: List[str]
    keywords: List[str]
    sources: List[SourceConfig]
    llm_relevance_threshold: int
    fallback_broaden: bool = False
    fallback_keywords: Optional[List[str]] = None
    min_articles_before_fallback: int = 0
    skip_if_no_relevant: bool = False
    language: str = "en"
    min_keyword_matches: int = 1  # Minimum keyword matches required (default 1)
    keywords_broad: Optional[List[str]] = None  # Broader context keywords for matching


@dataclass
class CategoryConfig:
    """Configuration for a category containing multiple topics"""
    name: str
    language: str  # "en" or "ja"
    topics: List[TopicConfig]


@dataclass
class UserConfig:
    """Main user configuration"""
    name: str
    email: str
    categories: List[CategoryConfig]