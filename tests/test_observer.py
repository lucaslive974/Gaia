from pyingestion.observer import EventBus, PipelineEvents


def test_event_bus_pub_sub():
    bus = EventBus()

    events_received = []

    def on_extraction_started(session, total_files, **kwargs):
        events_received.append(("started", total_files))

    bus.on(PipelineEvents.EXTRACTION_STARTED, on_extraction_started)

    # Should be received
    bus.emit(PipelineEvents.EXTRACTION_STARTED, session=None, total_files=5)

    assert len(events_received) == 1
    assert events_received[0] == ("started", 5)


def test_event_bus_error_isolation():
    bus = EventBus()

    def crash_listener(*args, **kwargs):
        raise ValueError("I crash the pipeline")

    def safe_listener(*args, **kwargs):
        kwargs["state"]["safe_called"] = True

    bus.on(PipelineEvents.PAGE_PROCESSED, crash_listener)
    bus.on(PipelineEvents.PAGE_PROCESSED, safe_listener)

    state = {"safe_called": False}

    # The crash_listener will fail, but the emit method should catch it
    # and continue to call safe_listener without raising the exception.
    bus.emit(PipelineEvents.PAGE_PROCESSED, state=state)

    assert state["safe_called"] is True
