"""Registry for mapping action names to callables.

The registry acts as the central hub through which API endpoints
look up and execute actions.  Each action is registered under a unique
string key.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Optional, Any

logger = logging.getLogger(__name__)


class ActionRegistry:
    """Central storage for executable actions."""

    def __init__(self) -> None:
        self._actions: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, func: Callable[..., Any]) -> None:
        """Register a new action.

        If an action with the same name already exists it will be
        overwritten and a warning is logged.
        """
        if name in self._actions:
            logger.warning("Overwriting existing action '%s'", name)
        self._actions[name] = func

    def get(self, name: str) -> Optional[Callable[..., Any]]:
        """Retrieve a registered action by name."""
        return self._actions.get(name)

    def execute(self, name: str, **kwargs: Any) -> Any:
        """Execute an action by name with keyword arguments."""
        action = self.get(name)
        if action is None:
            raise KeyError(f"Action '{name}' not found")
        return action(**kwargs)
