import resend
import os
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self):
        # Initialize Resend with API key from environment
        resend.api_key = os.getenv("RESEND_API_KEY")
    
    def send_newsletter(self, html_content: str, recipient_email: str, subject: str = None) -> bool:
        """
        Send the newsletter via Resend.
        
        Args:
            html_content: HTML content of the newsletter
            recipient_email: Email address to send to
            subject: Subject line (defaults to a standard subject)
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not subject:
            subject = f"Daily Brief - Global Finance & Japan Industry Newsletter - {datetime.now().strftime('%Y-%m-%d')}"
        
        try:
            # Get sender email from environment variable, default to onboarding@resend.dev
            from_email = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
            sender_name = "Daily Brief"
            
            params = {
                "from": f"{sender_name} <{from_email}>",
                "to": [recipient_email],
                "subject": subject,
                "html": html_content,
            }
            
            email = resend.Emails.send(params)
            logger.info(f"Newsletter sent successfully with ID: {email['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def save_newsletter_locally(self, html_content: str, filename: str = None) -> str:
        """
        Save the newsletter HTML to a local file as backup.
        
        Args:
            html_content: HTML content of the newsletter
            filename: Custom filename (defaults to timestamped filename)
        
        Returns:
            str: Path to the saved file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"newsletter_{timestamp}.html"
        
        # Create output directory if it doesn't exist
        os.makedirs('output', exist_ok=True)
        
        filepath = os.path.join('output', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Newsletter saved locally to: {filepath}")
        return filepath