"""FDIC ingestion components for the bank-risk platform."""

from .fdic_client import FdicClient, FdicClientConfig, FinancialsQuery

__all__: list[str] = ["FdicClient", "FdicClientConfig", "FinancialsQuery"]

