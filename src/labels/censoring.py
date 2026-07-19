"""Small pure boundary helpers mirroring the documented SQL label policy."""

from __future__ import annotations

from datetime import date


def positive_within_horizon(reporting_date: date, event_date: date, horizon_end: date) -> bool:
    return reporting_date < event_date <= horizon_end


def has_complete_followup(horizon_end: date, surveillance_end: date) -> bool:
    return horizon_end <= surveillance_end


def competing_exit_precedes_event(competing_exit: date, event_date: date | None, horizon_end: date) -> bool:
    return competing_exit <= horizon_end and (event_date is None or competing_exit < event_date)
