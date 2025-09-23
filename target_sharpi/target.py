"""Sharpi target class."""

from __future__ import annotations

from singer_sdk import typing as th
from singer_sdk.target_base import Target

from target_sharpi.sinks import (
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

    def get_sink_class(self, stream_name: str) -> type:
        """Return the appropriate sink class for the given stream name."""
        sink_mapping = {
            "products": ProductsSink,
            "prices": PricesSink,
            "clients": CustomersSink,
        }
        if stream_name not in sink_mapping:
            raise ValueError(f"Unsupported stream: {stream_name}. Supported streams are: {', '.join(sink_mapping.keys())}")
        return sink_mapping[stream_name]

    def get_sink(self, stream_name: str, *, record: dict | None = None, schema: dict | None = None, key_properties: list[str] | None = None):
        """Get a sink for the given stream name with stream_name in context."""
        sink = super().get_sink(stream_name, record=record, schema=schema, key_properties=key_properties)
        return sink

    def _process_record_message(self, message_dict: dict) -> None:
        """Override to inject stream_name into context before processing."""
        stream_name = message_dict.get("stream")
        if stream_name:
            # Get the record and schema from the message
            record = message_dict.get("record", {})
            schema = message_dict.get("schema")
            key_properties = message_dict.get("key_properties")

            # Get the sink for this stream
            sink = self.get_sink(stream_name, record=record, schema=schema, key_properties=key_properties)

            # Create context with stream_name
            context = {"stream_name": stream_name}

            # Process the record with the updated context
            sink.process_record(record, context)
        else:
            # If no stream name, log warning but continue with parent implementation
            self.logger.warning("Record message missing 'stream' field, using fallback processing")
            super()._process_record_message(message_dict)


if __name__ == "__main__":
    TargetSharpi.cli()
