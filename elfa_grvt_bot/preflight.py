"""Preflight checks for the Elfa GRVT bot."""
import os
import logging
import httpx
from typing import Dict, Optional
from decimal import Decimal
from .elfa_client import ElfaClient
from .grvt_client import GrvtClient

class PreflightError(Exception):
    """Base class for preflight errors."""
    pass

class Preflight:
    """
    Runs preflight checks before starting the bot.
    Verifies configurations, credentials, and dependencies.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("preflight")
    
    async def run_checks(self) -> bool:
        """Run all preflight checks."""
        checks = [
            self.check_env_vars,
            self.check_elfa_connection,
            self.check_grvt_connection,
            self.check_telegram_config
        ]
        
        results = []
        for check in checks:
            try:
                results.append(await check())
                self.logger.info(f"Preflight check passed: {check.__name__}")
            except PreflightError as e:
                self.logger.error(f"Preflight check failed: {check.__name__} - {str(e)}")
                results.append(False)
        
        return all(results)
    
    async def check_env_vars(self) -> bool:
        """Verify required environment variables are set."""
        required_vars = [
            "ELFA_API_KEY",
            "GRVT_TRADING_API_KEY",
            "GRVT_TRADING_PRIVATE_KEY"
        ]
        
        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            raise PreflightError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True
    
    async def check_elfa_connection(self) -> bool:
        """Verify Elfa API connection."""
        from .elfa_client import ElfaClient
        
        try:
            client = ElfaClient(os.getenv("ELFA_API_KEY"))
            # Simple validation request
            result = await client.validate_query({"conditions": {"AND": []}})
            if not result.get("valid", False):
                raise PreflightError("Elfa validation query failed")
            return True
        except Exception as e:
            raise PreflightError(f"Elfa connection failed: {str(e)}")
    
    async def check_grvt_connection(self) -> bool:
        """Verify GRVT API connection."""
        from .grvt_client import GrvtClient
        
        try:
            client = GrvtClient(
                os.getenv("GRVT_TRADING_API_KEY"),
                os.getenv("GRVT_TRADING_PRIVATE_KEY")
            )
            # Simple login check
            if not await client.login():
                raise PreflightError("GRVT login failed")
            return True
        except Exception as e:
            raise PreflightError(f"GRVT connection failed: {str(e)}")
    
    async def check_telegram_config(self) -> bool:
        """Verify Telegram configuration (optional)."""
        if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
            self.logger.warning("Telegram notifications disabled - missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
            return True  # Telegram is optional
            
        # If we have the vars, try a simple API call
        try:
            import httpx
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                if not response.json().get("ok", False):
                    raise PreflightError("Telegram bot token validation failed")
            return True
        except Exception as e:
            raise PreflightError(f"Telegram connection failed: {str(e)}")