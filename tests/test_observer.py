import queue
from pydocstruct import QueueObserver


def test_queue_observer_puts_events():
    q = queue.Queue()
    observer = QueueObserver(q)

    observer.on_start(5)
    assert q.get() == ("START", 5)

    observer.on_file_start(1, "test.pdf", 1.5)
    assert q.get() == ("FILE_START", (1, "test.pdf", 1.5))

    observer.on_page_start(3, 10)
    assert q.get() == ("PAGE_START", (3, 10))

    observer.on_page_processed(True, 3, 0, 3, 10)
    assert q.get() == ("PAGE_PROCESSED", (True, 3, 0, 3, 10))

    observer.on_file_complete(1, 100.0)
    assert q.get() == ("FILE_COMPLETE", (1, 100.0))

    observer.on_complete(3, 10)
    assert q.get() == ("COMPLETE", (3, 10))

    observer.on_error("Something broke")
    assert q.get() == ("ERROR", "Something broke")
