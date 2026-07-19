"""Typed FDIC BankFind Suite API connector with bounded retries."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.message import Message
from typing import Callable, Protocol

from .schema import ValidatedPage, validate_response


LOGGER = logging.getLogger(__name__)


class FdicClientError(RuntimeError):
    """Base class for actionable FDIC client errors."""


class FdicHttpError(FdicClientError):
    """Raised for non-retryable HTTP errors."""


class FdicRetryExhaustedError(FdicClientError):
    """Raised after all retryable attempts fail."""


class FdicResponseDecodeError(FdicClientError):
    """Raised when a successful response is not valid JSON."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: dict[str, str]
    body: bytes


class HttpTransport(Protocol):
    def get(self, url: str, headers: dict[str, str], timeout_seconds: int) -> HttpResponse: ...


class UrllibTransport:
    """External HTTP transport for the FDIC API."""

    def get(self, url: str, headers: dict[str, str], timeout_seconds: int) -> HttpResponse:
        request = urllib.request.Request(url=url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                response_headers: Message = response.headers
                return HttpResponse(
                    status=response.status,
                    headers={key.lower(): value for key, value in response_headers.items()},
                    body=response.read(),
                )
        except urllib.error.HTTPError as error:
            return HttpResponse(
                status=error.code,
                headers={key.lower(): value for key, value in error.headers.items()},
                body=error.read(),
            )
        except urllib.error.URLError as error:
            reason: object = error.reason
            if isinstance(reason, TimeoutError):
                raise TimeoutError(f"FDIC request timed out: url={url}") from error
            raise ConnectionError(f"FDIC request failed: url={url}, reason={reason}") from error


@dataclass(frozen=True)
class FdicClientConfig:
    base_url: str
    timeout_seconds: int
    max_attempts: int
    backoff_base_seconds: float
    user_agent: str
    allowed_unexpected_fields: frozenset[str]
    required_fields: frozenset[str]


@dataclass(frozen=True)
class FinancialsQuery:
    filters: str
    fields: tuple[str, ...]
    sort_by: str
    sort_order: str
    limit: int
    offset: int
    output_format: str


@dataclass(frozen=True)
class FetchedPage:
    url: str
    status: int
    attempts: int
    body: bytes
    validated: ValidatedPage


def query_parameters(query: FinancialsQuery) -> dict[str, str]:
    return {
        "filters": query.filters,
        "fields": ",".join(query.fields),
        "sort_by": query.sort_by,
        "sort_order": query.sort_order,
        "limit": str(query.limit),
        "offset": str(query.offset),
        "format": query.output_format,
    }


def replace_offset(query: FinancialsQuery, offset: int) -> FinancialsQuery:
    return FinancialsQuery(
        filters=query.filters,
        fields=query.fields,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        limit=query.limit,
        offset=offset,
        output_format=query.output_format,
    )


def retry_delay_seconds(
    attempt: int, backoff_base_seconds: float, retry_after_header: str | None
) -> float:
    if retry_after_header is not None:
        try:
            retry_after: float = float(retry_after_header)
        except ValueError:
            retry_after = -1.0
        if retry_after >= 0:
            return retry_after
    return backoff_base_seconds * (2 ** (attempt - 1))


class FdicClient:
    """Connector interface for deterministic FDIC Financials API requests."""

    def __init__(
        self,
        config: FdicClientConfig,
        transport: HttpTransport,
        sleeper: Callable[[float], None],
    ) -> None:
        self._config = config
        self._transport = transport
        self._sleeper = sleeper

    @classmethod
    def live(cls, config: FdicClientConfig) -> "FdicClient":
        return cls(config=config, transport=UrllibTransport(), sleeper=time.sleep)

    def build_url(self, endpoint: str, query: FinancialsQuery) -> str:
        base: str = self._config.base_url.rstrip("/")
        encoded: str = urllib.parse.urlencode(query_parameters(query), safe=",:!()")
        return f"{base}/{endpoint.lstrip('/')}?{encoded}"

    def fetch_page(self, endpoint: str, query: FinancialsQuery) -> FetchedPage:
        url: str = self.build_url(endpoint, query)
        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": self._config.user_agent,
        }
        last_error: Exception | None = None
        for attempt in range(1, self._config.max_attempts + 1):
            LOGGER.info(
                "fdic_request_start",
                extra={"url": url, "attempt": attempt, "timeout_seconds": self._config.timeout_seconds},
            )
            try:
                response: HttpResponse = self._transport.get(
                    url=url,
                    headers=headers,
                    timeout_seconds=self._config.timeout_seconds,
                )
            except (TimeoutError, ConnectionError) as error:
                last_error = error
                if attempt == self._config.max_attempts:
                    break
                delay: float = retry_delay_seconds(
                    attempt=attempt,
                    backoff_base_seconds=self._config.backoff_base_seconds,
                    retry_after_header=None,
                )
                LOGGER.warning(
                    "fdic_request_retry",
                    extra={
                        "url": url,
                        "attempt": attempt,
                        "max_attempts": self._config.max_attempts,
                        "delay_seconds": delay,
                        "error_type": type(error).__name__,
                    },
                )
                self._sleeper(delay)
                continue
            if response.status == 429 or 500 <= response.status <= 599:
                last_error = FdicHttpError(
                    f"Retryable FDIC response: status={response.status}, url={url}, "
                    f"body={response.body[:500]!r}"
                )
                if attempt == self._config.max_attempts:
                    break
                delay = retry_delay_seconds(
                    attempt=attempt,
                    backoff_base_seconds=self._config.backoff_base_seconds,
                    retry_after_header=response.headers.get("retry-after"),
                )
                LOGGER.warning(
                    "fdic_http_retry",
                    extra={
                        "url": url,
                        "status": response.status,
                        "attempt": attempt,
                        "max_attempts": self._config.max_attempts,
                        "delay_seconds": delay,
                    },
                )
                self._sleeper(delay)
                continue
            if response.status < 200 or response.status >= 300:
                raise FdicHttpError(
                    f"FDIC request rejected: status={response.status}, url={url}, "
                    f"body={response.body[:1000]!r}"
                )
            try:
                payload: object = json.loads(response.body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise FdicResponseDecodeError(
                    f"FDIC response is not valid UTF-8 JSON: status={response.status}, url={url}, "
                    f"body={response.body[:500]!r}"
                ) from error
            validated: ValidatedPage = validate_response(
                payload=payload,
                required_fields=self._config.required_fields,
                requested_fields=frozenset(query.fields),
                allowed_unexpected_fields=self._config.allowed_unexpected_fields,
            )
            LOGGER.info(
                "fdic_request_success",
                extra={
                    "url": url,
                    "status": response.status,
                    "attempt": attempt,
                    "row_count": len(validated.records),
                    "expected_total": validated.total,
                },
            )
            return FetchedPage(
                url=url,
                status=response.status,
                attempts=attempt,
                body=response.body,
                validated=validated,
            )
        if last_error is None:
            raise FdicRetryExhaustedError(f"FDIC retry loop ended without an error: url={url}")
        raise FdicRetryExhaustedError(
            f"FDIC request failed after {self._config.max_attempts} attempts: url={url}, "
            f"last_error={last_error}"
        ) from last_error
