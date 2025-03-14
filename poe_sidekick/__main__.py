"""Main entry point for POE Sidekick."""

import asyncio
import logging
import signal
import sys
from typing import Any

from poe_sidekick.core.engine import Engine, WindowError

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_signal_name(sig: int) -> str:
    """Get a human-readable name for a signal number.

    Args:
        sig: The signal number.

    Returns:
        str: Human-readable signal name.
    """
    signal_names: dict[int, str] = {
        signal.SIGINT: "keyboard interrupt (Ctrl+C)",
        signal.SIGTERM: "termination request",
        signal.SIGBREAK: "break signal",
    }
    return signal_names.get(sig) or f"signal {sig}"


async def handle_shutdown(engine: Engine, sig: int) -> None:
    """Handle system signals for graceful shutdown.

    Args:
        engine: The POE Sidekick engine instance.
        sig: The signal number received.
    """
    logger.info(f"Received {get_signal_name(sig)}, shutting down gracefully...")
    await engine.stop()


async def main() -> None:
    """Start the POE Sidekick application."""
    engine = Engine()
    main_task = None

    def signal_handler(sig: int, _: Any) -> None:
        logger.info(f"Received {get_signal_name(sig)}, initiating shutdown...")
        if main_task:
            main_task.cancel()

    # Set up signal handlers for graceful shutdown
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, signal_handler)

    try:
        main_task = asyncio.current_task()
        await engine.start()

        # Wait indefinitely while the engine is running
        while engine.is_running:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("Main task cancelled, shutting down...")
        await engine.stop()
    except WindowError as e:
        logger.exception(e.message)  # User-friendly message with stack trace
        sys.exit(1)
    except Exception:
        logger.exception("An unexpected error occurred. Please report this issue")
        sys.exit(1)
    finally:
        await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
