"""Tests for the base workflow implementation."""

from typing import Any

import pytest
from numpy.typing import NDArray

from poe_sidekick.core.module import BaseModule, ModuleConfig
from poe_sidekick.core.workflow import (
    BaseWorkflow,
    ModuleActivationError,
    WorkflowError,
)


class MockModuleError(Exception):
    """Base exception for mock module errors."""

    pass


class MockActivationError(MockModuleError):
    """Raised when mock module activation fails."""

    def __init__(self) -> None:
        super().__init__("Mock activation failed")


class MockDeactivationError(MockModuleError):
    """Raised when mock module deactivation fails."""

    def __init__(self) -> None:
        super().__init__("Mock deactivation failed")


class MockModule(BaseModule):
    """Mock module for testing workflows."""

    def __init__(self, fail_activate: bool = False, fail_deactivate: bool = False) -> None:
        config = ModuleConfig(name="mock_module")
        services: dict[str, Any] = {}  # Empty services dict for testing
        super().__init__(config=config, services=services)
        self.fail_activate = fail_activate
        self.fail_deactivate = fail_deactivate
        self.activate_called = False
        self.deactivate_called = False
        self.process_frame_called = False

    async def _on_activate(self) -> None:
        """Mock implementation of abstract _on_activate."""
        self.activate_called = True
        if self.fail_activate:
            raise MockActivationError()

    async def _on_deactivate(self) -> None:
        """Mock implementation of abstract _on_deactivate."""
        self.deactivate_called = True
        if self.fail_deactivate:
            raise MockDeactivationError()

    async def _process_frame(self, frame: NDArray[Any]) -> None:
        """Mock implementation of abstract _process_frame."""
        self.process_frame_called = True


class TestWorkflow(BaseWorkflow):
    """Test workflow implementation."""

    async def execute(self) -> None:
        await self.activate_modules()
        try:
            # Simple test workflow that just activates/deactivates modules
            pass
        finally:
            await self.deactivate_modules()


@pytest.mark.asyncio
async def test_workflow_module_activation() -> None:
    """Test successful module activation."""
    module1 = MockModule()
    module2 = MockModule()
    workflow = TestWorkflow([module1, module2])

    await workflow.activate_modules()

    assert workflow.active
    assert module1.active
    assert module2.active
    assert module1.activate_called
    assert module2.activate_called


@pytest.mark.asyncio
async def test_workflow_module_deactivation() -> None:
    """Test successful module deactivation."""
    module1 = MockModule()
    module2 = MockModule()
    workflow = TestWorkflow([module1, module2])

    await workflow.activate_modules()
    await workflow.deactivate_modules()

    assert not workflow.active
    assert not module1.active
    assert not module2.active
    assert module1.deactivate_called
    assert module2.deactivate_called


@pytest.mark.asyncio
async def test_workflow_activation_failure() -> None:
    """Test handling of module activation failure."""
    module1 = MockModule()
    module2 = MockModule(fail_activate=True)
    module3 = MockModule()
    workflow = TestWorkflow([module1, module2, module3])

    with pytest.raises(ModuleActivationError):
        await workflow.activate_modules()

    # Check that module1 was deactivated after module2's activation failed
    assert not workflow.active
    assert not module1.active
    assert module1.deactivate_called
    # module3 should never have been activated
    assert not module3.activate_called


@pytest.mark.asyncio
async def test_workflow_deactivation_failure() -> None:
    """Test handling of module deactivation failure."""
    module1 = MockModule()
    module2 = MockModule(fail_deactivate=True)
    workflow = TestWorkflow([module1, module2])

    await workflow.activate_modules()

    with pytest.raises(WorkflowError):
        await workflow.deactivate_modules()

    # Check that we attempted to deactivate all modules
    assert not workflow.active
    assert module1.deactivate_called
    assert module2.deactivate_called


@pytest.mark.asyncio
async def test_workflow_execute() -> None:
    """Test workflow execution with proper cleanup."""
    module1 = MockModule()
    module2 = MockModule()
    workflow = TestWorkflow([module1, module2])

    await workflow.execute()

    # Check that modules were properly activated and deactivated
    assert not workflow.active
    assert not module1.active
    assert not module2.active
    assert module1.activate_called
    assert module2.activate_called
    assert module1.deactivate_called
    assert module2.deactivate_called


@pytest.mark.asyncio
async def test_base_workflow_execute_not_implemented() -> None:
    """Test that base workflow execute() raises NotImplementedError."""
    workflow = BaseWorkflow([])
    with pytest.raises(NotImplementedError):
        await workflow.execute()


@pytest.mark.asyncio
async def test_workflow_skip_already_active_modules() -> None:
    """Test that workflow skips activation of already active modules."""
    module1 = MockModule()
    module2 = MockModule()

    # Pre-activate module1
    await module1.activate()
    module1.activate_called = False  # Reset for test

    workflow = TestWorkflow([module1, module2])
    await workflow.activate_modules()

    # module1 should not have been activated again
    assert not module1.activate_called
    # module2 should have been activated
    assert module2.activate_called
    assert workflow.active
    assert module1.active
    assert module2.active
