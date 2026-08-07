"""Synchronous Observer-pattern EventBus — per-engine instance, not a singleton.

Follows event-system spec §2 and 13-event-system.md §4.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from typing import Callable

from fortress_engine.events.event_types import EngineEvent

EventHandler = Callable[[EngineEvent], None]


class EventBus:
    """Synchronous event dispatch with per-handler error isolation.

    Handlers are registered by event type string and called in FIFO
    registration order. The special type ``"*"`` receives every event.
    Handler exceptions are caught and logged to stderr in ``__debug__``
    mode; they never propagate to ``emit()`` callers or block other
    handlers.

    Each ``EventBus`` instance is independent — there is no global
    singleton.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register *handler* for *event_type*.

        Use ``"*"`` to subscribe to all event types.
        """
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove *handler* from *event_type*.

        Silently succeeds if the handler was not registered.
        """
        try:
            self._subscribers[event_type].remove(handler)
        except ValueError:
            pass

    def emit(self, event: EngineEvent) -> None:
        """Dispatch *event* to all matching handlers.

        Handlers subscribed to the specific *event.type* run first
        (in registration order), followed by wildcard ``"*"`` handlers.
        Exceptions in individual handlers are caught and do not prevent
        other handlers from running or escape to the caller.
        """
        handlers = (
            self._subscribers.get(event.type, [])
            + self._subscribers.get("*", [])
        )
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                if __debug__:
                    handler_name = getattr(handler, "__name__", repr(handler))
                    print(
                        f"[EventBus] Error in handler {handler_name} "
                        f"for event {event.type}: {exc}",
                        file=sys.stderr,
                    )
