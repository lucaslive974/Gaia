import unittest
import queue
from gaia import QueueObserver


class TestObserver(unittest.TestCase):
    def test_queue_observer_puts_events(self):
        q = queue.Queue()
        observer = QueueObserver(q)
        
        observer.on_start(5)
        self.assertEqual(q.get(), ("START", 5))
        
        observer.on_file_start(1, "test.pdf", 1.5)
        self.assertEqual(q.get(), ("FILE_START", (1, "test.pdf", 1.5)))
        
        observer.on_page_start(3, 10)
        self.assertEqual(q.get(), ("PAGE_START", (3, 10)))
        
        observer.on_page_processed(True, 3, 0, 3, 10)
        self.assertEqual(q.get(), ("PAGE_PROCESSED", (True, 3, 0, 3, 10)))

        
        observer.on_file_complete(1, 100.0)
        self.assertEqual(q.get(), ("FILE_COMPLETE", (1, 100.0)))
        
        observer.on_complete(3, 10)
        self.assertEqual(q.get(), ("COMPLETE", (3, 10)))
        
        observer.on_error("Something broke")
        self.assertEqual(q.get(), ("ERROR", "Something broke"))


if __name__ == "__main__":
    unittest.main()
