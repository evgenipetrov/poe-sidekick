"""Loot detection workflow implementation."""

import asyncio
import logging

from ..core.workflow import BaseWorkflow
from ..plugins.loot_manager.module import LootModule

logger = logging.getLogger(__name__)


class LootWorkflow(BaseWorkflow):
    """Workflow for loot detection.

    This is a lean initial implementation that just activates
    the loot module and logs detection events.
    """

    def __init__(self, loot_module: LootModule):
        """Initialize the loot workflow.

        Args:
            loot_module: The loot module instance to use
        """
        super().__init__([loot_module])
        self.loot_module = loot_module

    async def execute(self) -> None:
        """Execute the loot detection workflow."""
        logger.info("Starting loot detection workflow")
        await self.activate_modules()
        try:
            # For now, just keep the module active
            # We'll add more sophisticated logic later
            while True:
                await asyncio.sleep(1)
        finally:
            await self.deactivate_modules()
            logger.info("Loot detection workflow stopped")
