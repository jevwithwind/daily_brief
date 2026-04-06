#!/usr/bin/env python3
"""
Diagnostic script to analyze the Daily Brief pipeline issues
"""
import os
import sys
import yaml
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import requests
import feedparser

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import Article, TopicConfig, SourceConfig
from collectors.rss_collector import RSSCollector
from collectors.google_news_collector import GoogleNewsCollector
from filters.time_filter import filter_by_time
from filters.keyword_filter import filter_by_keywords


def get_sample_articles_after_time_filter(topic_config: TopicConfig) -> List[Article]:
    """Get articles after time filtering but before keyword filtering"""
    all_articles = []
    
    # Collect from all sources
    for source in topic_config.sources:
        if source.type == 'rss':
            collector = RSSCollector()
            articles = collector.collect(source)
            all_articles.extend(articles)
        elif source.type == 'google_news':
            collector = GoogleNewsCollector()
            articles = collector.collect(source)
            all_articles.extend(articles)
    
    # Apply time filter (48 hours)
    time_filtered = filter_by_time(all_articles, hours=48)
    return time_filtered


def analyze_keyword_matching(articles: List[Article], topic_config: TopicConfig) -> List[Dict[str, Any]]:
    """Analyze why articles failed the keyword filter"""
    failed_articles = []
    
    strict_keywords = topic_config.keywords
    broad_keywords = getattr(topic_config, 'keywords_broad', []) or []
    
    for article in articles:
        # Convert article text to lowercase for comparison
        article_text = f"{article.title} {article.summary}".lower()
        
        # Check for strict keyword matches
        strict_matches = [kw for kw in strict_keywords if kw.lower() in article_text]
        strict_match = len(strict_matches) > 0
        
        # Check for broad keyword matches
        broad_matches = [kw for kw in broad_keywords if kw.lower() in article_text]
        broad_match = len(broad_matches) >= 2
        
        # If article would fail the keyword filter, add to failed list
        if not (strict_match or broad_match):
            failed_info = {
                'title': article.title,
                'summary': article.summary[:200] if article.summary else '',
                'source': article.source,
                'strict_keywords_tested': strict_keywords,
                'broad_keywords_tested': broad_keywords,
                'strict_matches': strict_matches,
                'broad_matches': broad_matches,
                'broad_match_count': len(broad_matches)
            }
            failed_articles.append(failed_info)
    
    return failed_articles


def main():
    # Load configuration
    with open('config/user_likaiwen.yaml', 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    # Find the specific topics
    topics_to_analyze = [
        "Japan Market Revival",
        "US-Japan Economic Ties", 
        "US-China Trade War"
    ]
    
    # Flatten all topics from all categories
    all_topics = []
    for category in config_data['categories']:
        for topic in category['topics']:
            all_topics.append((category, topic))
    
    print("="*80)
    print("DAILY BRIEF DIAGNOSTIC REPORT")
    print("="*80)
    
    # Part 1: Show keyword filter code
    print("\nPART 1: KEYWORD FILTER CODE")
    print("-"*50)
    with open('filters/keyword_filter.py', 'r', encoding='utf-8') as f:
        print(f.read())
    
    # Part 2: Show LLM relevance scoring code
    print("\nPART 2: LLM RELEVANCE SCORING CODE")
    print("-"*50)
    with open('filters/llm_relevance.py', 'r', encoding='utf-8') as f:
        print(f.read())
    
    # Part 3: Sample article data for failing topics
    print("\nPART 3: SAMPLE ARTICLES THAT FAILED KEYWORD FILTER")
    print("-"*50)
    
    for topic_name in topics_to_analyze:
        print(f"\nAnalyzing topic: {topic_name}")
        print("="*60)
        
        # Find the topic config
        topic_config = None
        category_config = None
        for cat, topic in all_topics:
            if topic['name'] == topic_name:
                category_config = cat
                topic_config = topic
                break
        
        if not topic_config:
            print(f"Topic '{topic_name}' not found in config")
            continue
        
        # Create TopicConfig object
        sources = []
        for src_data in topic_config['sources']:
            source_config = SourceConfig(
                type=src_data['type'],
                name=src_data['name'],
                url=src_data.get('url'),
                query=src_data.get('query')
            )
            sources.append(source_config)
        
        topic_cfg = TopicConfig(
            name=topic_config['name'],
            tags=topic_config.get('tags', []),
            keywords=topic_config['keywords'],
            sources=sources,
            llm_relevance_threshold=topic_config['llm_relevance_threshold'],
            keywords_broad=topic_config.get('keywords_broad', [])
        )
        
        # Get articles after time filter
        time_filtered_articles = get_sample_articles_after_time_filter(topic_cfg)
        print(f"Articles after time filter (48 hours): {len(time_filtered_articles)}")
        
        # Analyze which ones fail keyword filter
        failed_articles = analyze_keyword_matching(time_filtered_articles, topic_cfg)
        print(f"Articles that failed keyword filter: {len(failed_articles)}")
        
        # Print first 5 failed articles with detailed analysis
        for i, article in enumerate(failed_articles[:5]):
            print(f"\n  Article {i+1}:")
            print(f"    Title: {article['title']}")
            print(f"    Summary: {article['summary']}")
            print(f"    Source: {article['source']}")
            print(f"    Strict keywords tested: {article['strict_keywords_tested']}")
            print(f"    Broad keywords tested: {article['broad_keywords_tested']}")
            print(f"    Strict matches: {article['strict_matches']}")
            print(f"    Broad matches: {article['broad_matches']} ({article['broad_match_count']}/2 needed)")
    
    # Part 5: Show the current config
    print("\nPART 5: CURRENT CONFIG FILE")
    print("-"*50)
    with open('config/user_likaiwen.yaml', 'r', encoding='utf-8') as f:
        print(f.read())


if __name__ == "__main__":
    main()
