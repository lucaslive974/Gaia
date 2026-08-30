import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventBus:
    """
    A dynamic, string-based Event Bus for the ingestion pipeline.
    Replaces rigid GoF Observers.
    """

    def __init__(self):
        # Maps event strings (e.g., 'extraction.started') to a list of callables
        self._listeners: dict[str, list[Callable[..., Any]]] = defaultdict(list)

    def on(self, event_name: str, listener: Callable[..., Any]):
        """Subscribe a callable to a specific pipeline event."""
        self._listeners[event_name].append(listener)
        return self  # Allow chaining

    def off(self, event_name: str, listener: Callable[..., Any]):
        """Unsubscribe a callable from an event."""
        if listener in self._listeners[event_name]:
            self._listeners[event_name].remove(listener)

    def emit(self, event_name: str, *args: Any, **kwargs: Any):
        """
        Publish an event to all subscribed listeners.
        """
        for listener in self._listeners[event_name]:
            try:
                # Call the listener with the provided context
                listener(*args, **kwargs)
            except Exception as e:
                # ERROR ISOLATION:
                # If a custom logger/metrics module crashes, the pipeline survives.
                logger.error(
                    f"Observer {listener.__name__} failed handling event '{event_name}': {e}",
                    exc_info=True,
                )


class PipelineEvents:
    EXTRACTION_STARTED = "extraction.started"
    FILE_STARTED = "file.started"
    PAGE_STARTED = "page.started"
    PAGE_PROCESSED = "page.processed"
    FILE_COMPLETED = "file.completed"
    EXTRACTION_COMPLETED = "extraction.completed"
    EXTRACTION_ERROR = "extraction.error"


# Legacy compatibility exports if needed, or simply delete them and refactor everywhere.
# Since we are fully migrating to EventBus, we will drop ExtractionObserver, QueueObserver, DefaultExtractionObserver.
