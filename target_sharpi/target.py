"""Sharpi target class."""

from __future__ import annotations

from singer_sdk import typing as th
from singer_sdk.target_base import Target

from target_sharpi.sinks import (
    SharpiSink,
    ProductsSink,
    PricesSink,
    CustomersSink,
)


class TargetSharpi(Target):
    """Sample target for Sharpi."""

    name = "target-sharpi"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType(nullable=False),
            secret=True,  # Flag config as protected.
            required=True,
            title="Auth Token",
            description="The auth token for the Sharpi API",
        ),
    ).to_dict()

    default_sink_class = SharpiSink

    def get_sink_class(self, stream_name: str) -> type:
        """Return the appropriate sink class for the given stream name."""
        sink_mapping = {
            "products": ProductsSink,
            "prices": PricesSink,
            "customers": CustomersSink,
        }
        return sink_mapping.get(stream_name, self.default_sink_class)


if __name__ == "__main__":
    TargetSharpi.cli()
