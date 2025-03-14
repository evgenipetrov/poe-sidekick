"""Base workflow implementation for coordinating modules.

This module provides the foundation for creating workflows that coordinate
multiple modules to accomplish complex tasks. It handles module activation,
deactivation, error handling, and resource cleanup.
"""

import logging
from collections.abc import Sequence
from typing import Any

from poe_sidekick.core.module import BaseModule

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Base exception for workflow-related errors."""

    def __init__(self, errors: list[Exception]) -> None:
        super().__init__(f"Errors occurred while deactivating modules: {errors}")
        self.errors = errors


class ModuleActivationError(WorkflowError):
    """Raised when a module fails to activate."""

    def __init__(self, error: Any) -> None:
        super().__init__([error])
        self.error = error
        self.message = f"Failed to activate workflow modules: {error}"


class BaseWorkflow:
    """Base class for implementing workflows that coordinate multiple modules.

    A workflow is responsible for:
    1. Coordinating multiple modules to accomplish a complex task
    2. Managing module activation/deactivation
    3. Handling errors and ensuring proper cleanup
    4. Maintaining workflow state

    Example:
        class TradeWorkflow(BaseWorkflow):
            def __init__(self, trade_module, stash_module, inventory_module):
                super().__init__([trade_module, stash_module, inventory_module])

            async def execute(self):
                await self.activate_modules()
                try:
                    # Implement trade workflow steps
                    pass
                finally:
                    await self.deactivate_modules()
    """

    def __init__(self, modules: Sequence[BaseModule]) -> None:
        """Initialize the workflow with a sequence of modules.

        Args:
            modules: Sequence of BaseModule instances that this workflow will coordinate
        """
        self.modules = list(modules)
        self.active = False
        self._failed_activations: list[BaseModule] = []

    async def activate_modules(self) -> None:
        """Activate all modules required for this workflow.

        This method attempts to activate all modules in sequence. If any module
        fails to activate, all previously activated modules are deactivated
        before raising the error.

        Raises:
            ModuleActivationError: If any module fails to activate
        """
        self._failed_activations = []

        try:
            for module in self.modules:
                if not module.active:
                    await module.activate()
                    self._failed_activations.append(module)

            self.active = True
            self._failed_activations = []

        except Exception as e:
            # If any module fails to activate, deactivate all modules that were
            # successfully activated
            await self._cleanup_failed_activation()
            raise ModuleActivationError(e) from e

    async def deactivate_modules(self) -> None:
        """Deactivate all active modules.

        This method ensures all modules are deactivated, even if some
        deactivations fail. It attempts to deactivate all modules before
        raising any errors that occurred.
        """
        errors: list[Exception] = []

        for module in self.modules:
            if module.active:
                try:
                    await module.deactivate()
                except Exception as e:
                    errors.append(e)

        self.active = False

        if errors:
            raise WorkflowError(errors)

    async def _cleanup_failed_activation(self) -> None:
        """Clean up after a failed module activation.

        This method deactivates any modules that were successfully activated
        before the failure occurred.
        """
        for module in self._failed_activations:
            try:
                if module.active:
                    await module.deactivate()
            except Exception:
                logger.exception("Failed to deactivate module during cleanup")

        self._failed_activations = []
        self.active = False

    async def execute(self) -> None:
        """Execute the workflow.

        This method should be overridden by subclasses to implement the
        specific workflow logic. The base implementation ensures proper
        module activation and cleanup.

        Example implementation:
            async def execute(self):
                await self.activate_modules()
                try:
                    # Workflow-specific logic here
                    pass
                finally:
                    await self.deactivate_modules()
        """
        raise NotImplementedError("Workflow subclasses must implement execute() method")
