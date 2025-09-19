"""The base API client that can be extended to use for different services."""

from abc import ABC
from collections.abc import Iterable
import time
import random
from typing import Any, Literal
import logging
import requests
from http import HTTPStatus

from .exceptions import ApiRequestError, raise_for_status

LOG = logging.getLogger(__name__)


RequestMethods = Literal["GET", "POST", "PUT", "DELETE"]

JSONData = dict[str, Any]


class BaseClient(ABC):
    """Base API client."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 5.0,
        retries: int = 2,
        backoff: float = 0.2,
        max_backoff: float = 0.5,
        default_headers: dict[str, str] | None = None,
        session: requests.Session | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.max_backoff = max_backoff
        self.session = session or requests.Session()
        self.default_headers = dict(default_headers or {})

    def _request(self, method: RequestMethods, path: str, *,
                 expected_status: Iterable[int] = (200,),
                 timeout: float | None = None,
                 headers: dict[str, str] | None = None,
                 **kwargs: Any
                 ) -> JSONData | str | None:
        """Base request class"""
        api_url = f"{self.base_url}/{path}"
        combined_headers = {**self.default_headers, **(headers or {})}

        attempts = self.retries + 1
        for attempt in range(1, attempts):
            LOG.info("Request: %s %s - attempt %d", method, api_url, attempt)
            try:
                resp = self.session.request(
                    method, api_url, headers=combined_headers, 
                    timeout=timeout or self.timeout, **kwargs)

                if resp.status_code not in expected_status:
                    raise_for_status(resp.status_code, resp.text)
                
                # parse response
                if resp.status_code == HTTPStatus.NO_CONTENT or resp.content is None:
                    return None
                content_type = resp.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return resp.json()
                return resp.text  # resturn as string
            except (requests.ConnectionError, requests.Timeout):
                LOG.debug("Request attempt %d failed retrying %d times", attempt, attempts, extra={"url": api_url})
                self._sleep_with_jitter(attempt)
        raise ApiRequestError(f"Request {method} {api_url} failed")


    def _sleep_with_jitter(self, attempt: int) -> None:
        """Sleep time with a small jitter.
        
        Spaces out multiple request."""
        base = self.backoff * (2 ** (attempt - 1))
        sleep = random.uniform(0, min(self.max_backoff, base))
        time.sleep(sleep)


    # helper methods
    def get(self, path: str, **kwargs: Any):
        """Get request to entrypoint."""
        LOG.debug("Request: GET %s; params: %s", path, kwargs)
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any):
        """POST request to entrypoint."""
        LOG.debug("Request: POST %s; params: %s", path, kwargs)
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any):
        """PUT request to entrypoint."""
        LOG.debug("Request: PUT %s; params: %s", path, kwargs)
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any):
        """DELETE request to entrypoint."""
        LOG.debug("Request: DELETE %s; params: %s", path, kwargs)
        return self._request("DELETE", path, **kwargs)
