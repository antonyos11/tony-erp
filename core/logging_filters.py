import threading

_local = threading.local()

class RequestIDFilter:
    """Inject request_id & path & duration (ms) if available from middleware threadlocals."""
    def filter(self, record):
        record.request_id = getattr(_local, 'request_id', None)
        record.path = getattr(_local, 'request_path', None)
        record.duration_ms = getattr(_local, 'request_duration_ms', None)
        return True
