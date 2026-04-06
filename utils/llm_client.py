import os
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        api_key = os.getenv("DASHSCOPE_API_KEY")
        self.api_key = api_key
        if api_key:
            self.client = OpenAI(
                base_url="https://coding.dashscope.aliyuncs.com/v1",
                api_key=api_key
            )
        else:
            self.client = None
            print("Warning: DASHSCOPE_API_KEY not found. LLM functionality will be limited.")
    
    def get_relevance_score(self, article_title: str, article_summary: str, topic_name: str, category_name: str, topic_keywords: str, topic_broad_keywords: str, language: str = "en") -> Optional[Dict[str, Any]]:
        """
        Get relevance score for an article using qwen3-coder-plus model.
        Returns JSON with score (0-10) and reason.
        """
        if not self.client:
            logger.warning("LLM client not initialized due to missing API key. Returning default relevance score.")
            # Return a default score when API key is not available
            return {"score": 5, "reason": "Default score due to missing API key"}
        
        try:
            prompt = f"""You are a financial news relevance scorer. Rate how relevant this article is to the topic described below.

Topic: {topic_name}
Category: {category_name}
Key concepts: {topic_keywords}, {topic_broad_keywords}

Article title: {article_title}
Article summary: {article_summary}

Score from 0-10 where:
- 0-3: Not relevant
- 4-6: Somewhat relevant
- 7-10: Highly relevant

Respond ONLY in JSON: {{"score": int, "reason": "brief explanation in {language}"}}
"""
            
            response = self.client.chat.completions.create(
                model="qwen3-coder-plus",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            # Extract and parse the JSON response
            result_text = response.choices[0].message.content.strip()
            
            # Clean up potential markdown formatting
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            
            result = json.loads(result_text)
            return result
            
        except Exception as e:
            logger.error(f"Error getting relevance score: {str(e)}")
            return None
    
    def generate_summary(self, article_title: str, article_content: str, language: str = "en") -> Optional[str]:
        """
        Generate a summary of an article using kimi-k2.5 model.
        """
        if not self.client:
            logger.warning("LLM client not initialized due to missing API key. Returning original content as summary.")
            # Return a simple summary when API key is not available
            return f"Summary unavailable: {article_title[:100]}..."
        
        try:
            prompt = f"""Please provide a concise 2-3 sentence summary of the following article in {language}.
Focus on the key points and implications.

Article Title: {article_title}
Article Content: {article_content}

Summary:"""
            
            response = self.client.chat.completions.create(
                model="kimi-k2.5",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return None
    
    def generate_executive_summary(self, articles: list, topic_name: str, language: str = "en") -> Optional[str]:
        """
        Generate an executive summary for a group of articles in a topic.
        """
        if not self.client:
            logger.warning("LLM client not initialized due to missing API key. Returning topic name as executive summary.")
            # Return a simple summary when API key is not available
            return f"Executive summary for {topic_name} unavailable due to missing API key."
        
        try:
            article_texts = []
            for article in articles:
                article_texts.append(f"- {article.title}: {article.summary}")
            
            articles_str = "\n".join(article_texts[:5])  # Limit to first 5 articles to avoid token limits
            
            prompt = f"""Provide a 3-4 sentence executive summary synthesizing the key developments in '{topic_name}' based on these articles.
Write in a professional business tone in {language}.

Articles:
{articles_str}

Executive Summary:"""
            
            response = self.client.chat.completions.create(
                model="kimi-k2.5",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=400
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            return None