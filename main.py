#!/usr/bin/env python3
"""
Daily Brief - Global Finance & Japan Industry Newsletter
Main orchestrator script
"""

import argparse
import yaml
import os
import logging
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict
import sys

from models import UserConfig, TopicConfig, CategoryConfig, Article, SourceConfig
from utils.llm_client import LLMClient
from collectors.rss_collector import RSSCollector
from collectors.google_news_collector import GoogleNewsCollector
from collectors.prtimes_collector import PrTimesCollector
from filters.time_filter import filter_by_time
from filters.keyword_filter import filter_by_keywords
from filters.dedup import deduplicate_articles
from filters.llm_relevance import filter_by_llm_relevance
from summarizer.summarizer import Summarizer
from formatter.newsletter import NewsletterFormatter
from delivery.email_sender import EmailSender

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_brief.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> UserConfig:
    """Load user configuration from YAML file"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    # Parse the configuration into our data classes
    user_data = config_data['user']
    categories_data = config_data['categories']
    
    categories = []
    for cat_data in categories_data:
        topics = []
        for topic_data in cat_data['topics']:
            # Create source configs
            sources = []
            for src_data in topic_data['sources']:
                source_config = SourceConfig(
                    type=src_data['type'],
                    name=src_data['name'],
                    url=src_data.get('url'),
                    query=src_data.get('query'),
                    company_keywords=src_data.get('company_keywords')
                )
                sources.append(source_config)
            
            # Create topic config
            topic_config = TopicConfig(
                name=topic_data['name'],
                tags=topic_data['tags'],
                keywords=topic_data['keywords'],
                sources=sources,
                llm_relevance_threshold=topic_data['llm_relevance_threshold'],
                fallback_broaden=topic_data.get('fallback_broaden', False),
                fallback_keywords=topic_data.get('fallback_keywords'),
                min_articles_before_fallback=topic_data.get('min_articles_before_fallback', 0),
                skip_if_no_relevant=topic_data.get('skip_if_no_relevant', False),
                language=cat_data.get('language', 'en'),
                min_keyword_matches=topic_data.get('min_keyword_matches', 1),
                keywords_broad=topic_data.get('keywords_broad', [])
            )
            topics.append(topic_config)
        
        category_config = CategoryConfig(
            name=cat_data['name'],
            language=cat_data['language'],
            topics=topics
        )
        categories.append(category_config)
    
    user_config = UserConfig(
        name=user_data['name'],
        email=user_data['email'],
        categories=categories
    )
    
    return user_config


def collect_articles_from_sources(sources: List[SourceConfig]) -> List[Article]:
    """Collect articles from all sources, optimizing to avoid duplicate fetches"""
    articles = []
    
    # Group sources by URL to avoid duplicate fetches
    url_to_sources = {}
    for source in sources:
        if source.url:  # Only group by URL if it exists
            if source.url not in url_to_sources:
                url_to_sources[source.url] = []
            url_to_sources[source.url].append(source)
        else:
            # For sources without URLs (like Google News queries), process individually
            collector = None
            if source.type == 'rss':
                collector = RSSCollector()
            elif source.type == 'google_news':
                collector = GoogleNewsCollector()
            elif source.type == 'prtimes':
                collector = PrTimesCollector()
            
            if collector:
                try:
                    source_articles = collector.collect(source)
                    for article in source_articles:
                        article.source = source.name
                    articles.extend(source_articles)
                except Exception as e:
                    logger.warning(f"Error collecting from {source.name}: {str(e)}")
    
    # Process grouped sources (same URL)
    for url, source_configs in url_to_sources.items():
        # Use the first source config to collect (they all have the same URL)
        first_source = source_configs[0]
        collector = None
        
        if first_source.type == 'rss':
            collector = RSSCollector()
        elif first_source.type == 'google_news':
            collector = GoogleNewsCollector()
        elif first_source.type == 'prtimes':
            collector = PrTimesCollector()
        
        if collector:
            try:
                source_articles = collector.collect(first_source)
                # Assign the correct source name to each article based on the original source config
                for article in source_articles:
                    # Find which source config this article should be attributed to
                    # For now, assign to the first source, but in a real implementation
                    # you might want to be more sophisticated about this
                    article.source = first_source.name
                articles.extend(source_articles)
            except Exception as e:
                logger.warning(f"Error collecting from {first_source.name}: {str(e)}")
    
    return articles


def run_topic_pipeline(topic_config: TopicConfig, category_config: CategoryConfig, llm_client: LLMClient, hours: int = 48) -> List[Article]:
    """Run the full pipeline for a single topic"""
    logger.info(f"Processing topic: {topic_config.name}")
    
    # Collect articles from all sources
    all_articles = collect_articles_from_sources(topic_config.sources)
    logger.info(f"Collected {len(all_articles)} articles from sources for topic '{topic_config.name}'")
    
    # Apply time filter (filter to last N hours)
    time_filtered = filter_by_time(all_articles, hours=hours)
    logger.info(f"After time filter ({hours} hours): {len(time_filtered)} articles")
    
    # Apply keyword filter
    keyword_filtered = filter_by_keywords(time_filtered, topic_config)
    logger.info(f"After keyword filter: {len(keyword_filtered)} articles")
    
    # Check if we need to apply fallback keywords
    if (topic_config.fallback_broaden and
        len(keyword_filtered) < topic_config.min_articles_before_fallback and
        topic_config.fallback_keywords):
        
        logger.info(f"Applying fallback keywords for topic '{topic_config.name}'")
        
        # Create a temporary topic config with fallback keywords
        fallback_topic_config = TopicConfig(
            name=topic_config.name,
            tags=topic_config.tags,
            keywords=topic_config.fallback_keywords,
            sources=topic_config.sources,
            llm_relevance_threshold=topic_config.llm_relevance_threshold,
            language=topic_config.language
        )
        
        # Re-collect and filter with fallback keywords
        fallback_filtered = filter_by_keywords(time_filtered, fallback_topic_config)
        logger.info(f"After fallback keyword filter: {len(fallback_filtered)} articles")
        
        # Combine original and fallback results, removing duplicates by URL
        all_articles = keyword_filtered + fallback_filtered
        seen_urls = set()
        combined_articles = []
        for article in all_articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                combined_articles.append(article)
        keyword_filtered = combined_articles
    
    # Apply deduplication
    deduplicated = deduplicate_articles(keyword_filtered)
    logger.info(f"After deduplication: {len(deduplicated)} articles")
    
    # Apply LLM relevance filtering
    relevant_articles = filter_by_llm_relevance(deduplicated, topic_config, category_config, llm_client)
    logger.info(f"After LLM relevance filter: {len(relevant_articles)} articles")
    
    # Add topic and category info to articles
    for article in relevant_articles:
        article.topic_name = topic_config.name
        article.category_name = category_config.name
        article.language = topic_config.language
    
    return relevant_articles


def run_category_pipeline(category_config: CategoryConfig, llm_client: LLMClient, hours: int = 48) -> Dict[str, Any]:
    """Run the pipeline for all topics in a category"""
    logger.info(f"Processing category: {category_config.name}")
    
    category_result = {
        'language': category_config.language,
        'topics': {},
        'executive_summary': ''
    }
    
    for topic_config in category_config.topics:
        topic_articles = run_topic_pipeline(topic_config, category_config, llm_client, hours=hours)
        
        # Skip topics with no relevant articles if configured to do so
        if topic_config.skip_if_no_relevant and not topic_articles:
            logger.info(f"Skipping topic '{topic_config.name}' due to no relevant articles and skip_if_no_relevant=True")
            continue
        
        category_result['topics'][topic_config.name] = {
            'articles': topic_articles
        }
    
    return category_result


def main():
    parser = argparse.ArgumentParser(description='Daily Brief - Global Finance & Japan Industry Newsletter')
    parser.add_argument('--dry-run', action='store_true', help='Save HTML to output/ instead of sending email')
    parser.add_argument('--topic', type=str, help='Run only a specific topic')
    parser.add_argument('--category', type=str, help='Run only a specific category')
    parser.add_argument('--config', type=str, default='config/user_likaiwen.yaml', help='Path to config file')
    parser.add_argument('--hours', type=int, default=48, help='Number of hours to look back for articles (default: 48)')
    
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Load configuration
    logger.info(f"Loading configuration from {args.config}")
    user_config = load_config(args.config)
    
    # Override email from environment variable if available
    env_email = os.getenv("USER_EMAIL")
    if env_email:
        user_config.email = env_email
        logger.info(f"Email overridden from environment variable: {env_email}")
    
    # Initialize components
    llm_client = LLMClient()
    summarizer = Summarizer(llm_client)
    formatter = NewsletterFormatter()
    email_sender = EmailSender()
    
    # Determine which topics/categories to process
    categories_to_process = user_config.categories
    
    if args.category:
        categories_to_process = [cat for cat in categories_to_process if cat.name == args.category]
        if not categories_to_process:
            logger.error(f"Category '{args.category}' not found in configuration")
            return
    
    # If a specific topic is requested, find the correct category for it
    if args.topic:
        # Find the category that contains the requested topic
        found_category = None
        for cat in user_config.categories:
            for topic_config in cat.topics:
                if topic_config.name == args.topic:
                    found_category = cat
                    break
            if found_category:
                break
        
        if not found_category:
            logger.error(f"Topic '{args.topic}' not found in any category")
            return
        
        # Process only the found category
        categories_to_process = [found_category]
    
    # Collect articles for each category
    categorized_articles = {}
    
    for category_config in categories_to_process:
        if args.topic:
            # Run only the specific topic
            topic_found = False
            for topic_config in category_config.topics:
                if topic_config.name == args.topic:
                    topic_articles = run_topic_pipeline(topic_config, category_config, llm_client, hours=args.hours)
                    
                    # Skip if topic should be skipped when no relevant articles
                    if topic_config.skip_if_no_relevant and not topic_articles:
                        logger.info(f"Skipping topic '{topic_config.name}' due to no relevant articles and skip_if_no_relevant=True")
                    else:
                        categorized_articles[category_config.name] = {
                            'language': category_config.language,
                            'topics': {
                                topic_config.name: {
                                    'articles': topic_articles
                                }
                            }
                        }
                    topic_found = True
                    break
            
            if not topic_found:
                # This shouldn't happen if we found the right category earlier, but just in case
                logger.error(f"Topic '{args.topic}' not found in category '{category_config.name}'")
                return
        else:
            # Run all topics in the category
            category_result = run_category_pipeline(category_config, llm_client, hours=args.hours)
            
            # Only add category if it has topics with articles
            if category_result['topics']:
                categorized_articles[category_config.name] = category_result
    
    # Generate summaries for each topic
    for category_name, category_data in categorized_articles.items():
        for topic_name, topic_data in category_data['topics'].items():
            articles = topic_data['articles']
            
            # Generate executive summary for the topic
            topic_config = None
            for cat_config in user_config.categories:
                if cat_config.name == category_name:
                    for t_config in cat_config.topics:
                        if t_config.name == topic_name:
                            topic_config = t_config
                            break
                    break
            
            if topic_config and articles:
                topic_executive_summary = summarizer.summarize_topic(articles, topic_config)
                topic_data['executive_summary'] = topic_executive_summary
            
            # Generate individual article summaries
            summarized_articles = summarizer.process_articles_with_summaries(articles)
            topic_data['articles'] = summarized_articles
    
    # Format the newsletter
    logger.info("Formatting newsletter...")
    html_content = formatter.format_newsletter(categorized_articles, user_config.name)
    
    if args.dry_run:
        # Save to output directory instead of sending
        logger.info("Running in dry-run mode - saving newsletter to output/")
        saved_path = email_sender.save_newsletter_locally(html_content)
        logger.info(f"Newsletter saved to: {saved_path}")
    else:
        # Send the newsletter
        logger.info(f"Sending newsletter to: {user_config.email}")
        success = email_sender.send_newsletter(html_content, user_config.email)
        
        if success:
            logger.info("Newsletter sent successfully!")
        else:
            logger.error("Failed to send newsletter, saving locally as backup")
            email_sender.save_newsletter_locally(html_content)


if __name__ == "__main__":
    main()