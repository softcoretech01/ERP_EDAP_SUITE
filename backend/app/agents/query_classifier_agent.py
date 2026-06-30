import logging
import re

logger = logging.getLogger(__name__)

class QueryClassifierAgent:
    """
    Categorizes incoming queries into 4 distinct types for specialized processing:
    - 'sql': KPIs, raw data, simple counts (e.g. "Current procurement spend")
    - 'analytics': Insights, bottlenecks, causes (e.g. "Suppliers causing delays")
    - 'trend': Time-based charts, trends (e.g. "12 month spend trend")
    - 'prediction': Forecasting, risk (e.g. "Next month spend forecast")
    """
    
    def __init__(self):
        # Using regex to quickly classify query types
        self.rules = {
            "prediction": re.compile(r'\b(forecast|predict|prediction|risk|next month|next year|future|estimate)\b', re.IGNORECASE),
            "trend": re.compile(r'\b(trend|monthly|yearly|quarterly|over time|history|historical)\b', re.IGNORECASE),
            "analytics": re.compile(r'\b(bottleneck|delay|causing|why|analyze|analysis|insight|overspend|performance)\b', re.IGNORECASE)
        }

    def classify_query(self, query: str) -> str:
        """Returns one of: 'prediction', 'trend', 'analytics', 'sql'"""
        for category, pattern in self.rules.items():
            if pattern.search(query):
                return category
                
        # Fallback to standard SQL for KPIs and simple lists
        return "sql"

query_classifier_agent = QueryClassifierAgent()
