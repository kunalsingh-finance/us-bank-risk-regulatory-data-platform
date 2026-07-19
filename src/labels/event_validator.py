"""Pure event-separation predicates used by Phase 4 tests and orchestration."""

from __future__ import annotations

from datetime import date


def is_primary_failure(resolution_type: str) -> bool:
    return resolution_type == "FAILURE"


def exact_cert_match(event_cert: int, financial_certs: frozenset[int]) -> bool:
    return event_cert in financial_certs


def is_forward_event(reporting_date: date, event_date: date) -> bool:
    return event_date > reporting_date
