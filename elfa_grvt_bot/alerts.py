"""Alert system implementation for the Elfa GRVT bot."""
import logging
from typing import Optional, Dict

class ConsoleAlerts:
    """Simple console-based alert system."""
    
    def __init__(self):
        self.logger = logging.getLogger("alerts")
    
    async def emit(self, 
                 severity: str, 
                 category: str, 
                 message: str,
                 query_id: Optional[str] = None,
                 fire_event_id: Optional[str] = None,
                 details: Optional[Dict] = None):
        """Emit an alert to the console."""
        log_msg = f"[{severity.upper()}] {category}: {message}"
        if query_id:
            log_msg += f" (query_id: {query_id})"
        if fire_event_id:
            log_msg += f" (fire_event_id: {fire_event_id})"
            
        if severity == "error":
            self.logger.error(log_msg)
        elif severity == "warning":
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)
            
        if details:
            self.logger.debug(f"Details: {details}")