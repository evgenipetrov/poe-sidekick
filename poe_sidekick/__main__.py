"""Main entry point for POE Sidekick."""

import asyncio
import logging
import signal
import sys
from typing import Any

from poe_sidekick.core.engine import Engine

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def handle_signal(engine: Engine, sig: int, frame: Any) -> None:
    """Handle system signals for graceful shutdown.

    Args:
        engine: The POE Sidekick engine instance.
        sig: The signal number received.
    """
    logger.info(f"Received signal {sig}, initiating shutdown...")
    # Store task reference to prevent premature garbage collection
    shutdown_task = asyncio.create_task(engine.stop())  # noqa: F841, RUF006


async def main() -> None:
    """Start the POE Sidekick application."""
    engine = Engine()

    # Set up signal handlers for graceful shutdown
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, _: handle_signal(engine, s, _))

    try:
        await engine.start()

        # Keep the application running
        while engine.is_running:
            await asyncio.sleep(1)

    except Exception:
        logger.exception("Error occurred during execution")
        sys.exit(1)
    finally:
        await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
