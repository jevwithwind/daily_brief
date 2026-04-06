from jinja2 import Environment, FileSystemLoader
from typing import Dict, List, Any
from models import Article, CategoryConfig
import os
from datetime import datetime


class NewsletterFormatter:
    def __init__(self):
        # Set up Jinja2 environment with templates directory
        templates_dir = os.path.join(os.path.dirname(__file__), '..', 'templates')
        self.env = Environment(loader=FileSystemLoader(templates_dir))
        self.template = self.env.get_template('newsletter.html')
    
    def format_newsletter(self, categorized_articles: Dict[str, Dict[str, Any]], user_name: str) -> str:
        """
        Format the newsletter with categorized articles.
        
        Args:
            categorized_articles: Dictionary with category names as keys, 
                                each containing topics with their articles
            user_name: Name of the recipient
        """
        # Prepare data for template
        newsletter_data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'user_name': user_name,
            'categories': [],
            'toc_items': []  # Table of contents items
        }
        
        # Process each category
        for category_name, category_data in categorized_articles.items():
            category_info = {
                'name': category_name,
                'language': category_data.get('language', 'en'),
                'executive_summary': category_data.get('executive_summary', ''),
                'topics': []
            }
            
            # Add topics to table of contents
            for topic_name in category_data.get('topics', {}):
                toc_item = {
                    'category': category_name,
                    'topic': topic_name,
                    'anchor': f"{category_name.replace(' ', '_')}_{topic_name.replace(' ', '_')}"
                }
                newsletter_data['toc_items'].append(toc_item)
            
            # Process each topic in the category
            for topic_name, topic_data in category_data.get('topics', {}).items():
                topic_info = {
                    'name': topic_name,
                    'executive_summary': topic_data.get('executive_summary', ''),
                    'articles': topic_data.get('articles', []),
                    'anchor': f"{category_name.replace(' ', '_')}_{topic_name.replace(' ', '_')}"
                }
                category_info['topics'].append(topic_info)
            
            # Only add category if it has topics with articles
            if category_info['topics']:
                newsletter_data['categories'].append(category_info)
        
        # Render the template
        html_content = self.template.render(**newsletter_data)
        return html_content