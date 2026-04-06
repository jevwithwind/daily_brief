from abc import ABC, abstractmethod
from typing import List
from models import Article, SourceConfig


class BaseCollector(ABC):
    """Abstract base class for all collectors"""
    
    @abstractmethod
    def collect(self, source_config: SourceConfig) -> List[Article]:
        """Collect articles from the source"""
        pass