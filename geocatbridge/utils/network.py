from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_RETRIES = 2
DEFAULT_TIMEOUT = 10  # seconds
RETRY_STRATEGY = Retry(
    total=DEFAULT_RETRIES,
    status_forcelist=[429, 500, 502, 503, 504]
)


class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, *args, **kwargs):
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


BRIDGE_ADAPTER = TimeoutHTTPAdapter(max_retries=RETRY_STRATEGY)


class BridgeSession(Session):
    def __init__(self):
        super().__init__()
        self.mount('https://', BRIDGE_ADAPTER)
        self.mount('http://', BRIDGE_ADAPTER)
