"""Command-line interface for the Elfa GRVT bot."""

import argparse
import asyncio
import os
import uuid
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .core import Core
from .registry import Registry
from .elfa_client import ElfaClient
from .grvt_client import GrvtClient
from .alerts import ConsoleAlerts


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(prog="elfa-grvt-bot")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Initialize command
    init_parser = subparsers.add_parser("init", help="Initialize a new bot working directory")
    init_parser.add_argument("target_dir", nargs="?", default="~/elfa_grvt_bot")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run the bot")
    run_parser.add_argument("--config", default=".env", help="Path to config file")
    
    # Strategy commands
    strategy_parser = subparsers.add_parser("strategy", help="Manage strategies")
    strategy_subparsers = strategy_parser.add_subparsers(dest="strategy_command", required=True)
    
    # Strategy list
    list_parser = strategy_subparsers.add_parser("list", help="List all strategies")
    list_parser.add_argument("--status", help="Filter by status (active, fired, etc)")
    
    # Strategy create
    create_parser = strategy_subparsers.add_parser("create", help="Create a new strategy")
    create_parser.add_argument("title", help="Strategy title")
    create_parser.add_argument("description", help="Strategy description")
    create_parser.add_argument("eql", help="EQL query (JSON string or file path)")
    create_parser.add_argument("--side", choices=["buy", "sell"], required=True)
    create_parser.add_argument("--symbol", required=True)
    create_parser.add_argument("--amount", type=float, required=True)
    create_parser.add_argument("--order-type", choices=["market", "limit"], default="market")
    create_parser.add_argument("--price", type=float, help="Required for limit orders")
    create_parser.add_argument("--tp-pct", type=float, help="Take profit percentage")
    create_parser.add_argument("--sl-pct", type=float, help="Stop loss percentage")
    create_parser.add_argument("--leverage", type=int, help="Leverage to use")
    create_parser.add_argument("--max-notional", type=float, default=1000.0,
                             help="Max notional value in USD")
    
    # Strategy cancel
    cancel_parser = strategy_subparsers.add_parser("cancel", help="Cancel a strategy")
    cancel_parser.add_argument("query_id", help="Strategy query ID")
    
    # Fire commands
    fire_parser = subparsers.add_parser("fire", help="View fire events")
    fire_subparsers = fire_parser.add_subparsers(dest="fire_command", required=True)
    
    # Fire list
    fire_list_parser = fire_subparsers.add_parser("list", help="List fire events")
    fire_list_parser.add_argument("--query-id", help="Filter by query ID")
    fire_list_parser.add_argument("--outcome", help="Filter by outcome")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if args.command == "init":
        return handle_init(args)
    elif args.command == "run":
        return asyncio.run(handle_run(args))
    elif args.command == "strategy":
        return handle_strategy(args)
    elif args.command == "fire":
        return handle_fire(args)
    else:
        parser.print_help()
        return 1


def handle_init(args) -> int:
    """Handle init command."""
    target_dir = Path(args.target_dir).expanduser()
    print(f"Initializing at: {target_dir}")
    
    # Create directory structure
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "strategies").mkdir(exist_ok=True)
    
    # Create default .env file
    env_path = target_dir / ".env"
    if not env_path.exists():
        with open(env_path, "w") as f:
            f.write("""# Elfa GRVT Bot Configuration
ELFA_API_KEY=
GRVT_TRADING_API_KEY=
GRVT_TRADING_PRIVATE_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
""")
    
    print(f"Initialized at {target_dir}. Please edit {env_path} with your credentials.")
    return 0


async def handle_run(args) -> int:
    """Handle run command."""
    from dotenv import load_dotenv
    load_dotenv(args.config)
    
    registry = Registry()
    elfa = ElfaClient(os.getenv("ELFA_API_KEY"))
    grvt = GrvtClient(os.getenv("GRVT_TRADING_API_KEY"), 
                      os.getenv("GRVT_TRADING_PRIVATE_KEY"))
    alerts = ConsoleAlerts()
    
    core = Core(registry, elfa, grvt, alerts)

    # Login to GRVT at startup
    import logging as _lg
    _logger = _lg.getLogger(__name__)
    try:
        login_ok = await grvt.login()
        if login_ok:
            _logger.info(f"[GRVT] Login successful - account_id: {grvt.account_id}")
        else:
            _logger.error("[GRVT] Login failed")
    except Exception as _login_err:
        _logger.error(f"[GRVT] Login error: {_login_err}")
    
    try:
        await core.supervisor()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


def handle_strategy(args) -> int:
    """Handle strategy commands."""
    registry = Registry()
    
    if args.strategy_command == "list":
        strategies = registry.list_strategies(status=args.status)
        print(json.dumps(strategies, indent=2))
        return 0
    elif args.strategy_command == "create":
        # Parse EQL (either JSON string or file path)
        try:
            eql_raw = parse_eql_input(args.eql)
            eql = json.dumps(eql_raw) if isinstance(eql_raw, dict) else eql_raw
        except ValueError as e:
            print(f"Error parsing EQL: {e}", file=sys.stderr)
            return 1
            
        # Validate inputs
        if args.order_type == "limit" and not args.price:
            print("Error: --price is required for limit orders", file=sys.stderr)
            return 1
            
        # Create strategy
        new_query_id = str(uuid.uuid4())
        query_id = registry.add_strategy(
            query_id=new_query_id,
            title=args.title,
            description=args.description,
            eql_json=eql,
            side=args.side,
            symbol=args.symbol,
            amount=args.amount,
            order_type=args.order_type,
            price=args.price,
            tp_pct=args.tp_pct,
            sl_pct=args.sl_pct,
            leverage=args.leverage,
            max_notional_usd=args.max_notional
        )
        
        print(f"Created strategy with query_id: {query_id}")
        return 0
    elif args.strategy_command == "cancel":
        success = registry.cancel_strategy(args.query_id)
        if success:
            print(f"Cancelled strategy {args.query_id}")
            return 0
        else:
            print(f"Failed to cancel strategy {args.query_id}", file=sys.stderr)
            return 1
    else:
        print(f"Unknown strategy command: {args.strategy_command}", file=sys.stderr)
        return 1


def handle_fire(args) -> int:
    """Handle fire commands."""
    registry = Registry()
    
    if args.fire_command == "list":
        fires = registry.list_fires(query_id=args.query_id, outcome=args.outcome)
        print(json.dumps(fires, indent=2))
        return 0
    else:
        print(f"Unknown fire command: {args.fire_command}", file=sys.stderr)
        return 1


def parse_eql_input(eql_input: str) -> dict:
    """Parse EQL input which could be a JSON string or file path."""
    # Try to parse as JSON first
    try:
        return json.loads(eql_input)
    except json.JSONDecodeError:
        pass
    
    # Try to read as file
    try:
        with open(eql_input) as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        raise ValueError(f"Could not parse EQL input: {e}")


if __name__ == "__main__":
    raise SystemExit(main())


