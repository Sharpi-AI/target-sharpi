"""Sharpi target sink class, which handles writing streams."""

from __future__ import annotations

import requests
from typing import Any, Dict
from singer_sdk.sinks import RecordSink


class SharpiBaseSink(RecordSink):
    """Base Sharpi target sink class."""

    @property
    def api_key(self) -> str:
        """Get API key from config."""
        return self.config["api_key"]

    @property
    def base_url(self) -> str:
        """Get base URL for Sharpi API."""
        return "https://api.sharpi.com.br/v1/partner"

    def make_request(self, endpoint: str, data: Dict[str, Any]) -> None:
        """Make HTTP request to Sharpi API."""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

        self.logger.info("Making request to %s", url)
        self.logger.debug("Request data: %s", data)

        response = requests.post(url, json=data, headers=headers)

        self.logger.info("Response status code: %s", response.status_code)
        self.logger.debug("Response: %s", response.text)

        if response.status_code == 400:
            response_json = response.json()
            if "duplicate key" in response_json.get("message", ""):
                self.logger.warning("Duplicate record ignored for %s: %s", endpoint, data.get('code', 'unknown'))
                return
            response.raise_for_status()


class ProductsSink(SharpiBaseSink):
    """Sharpi products sink class."""

    def process_record(self, record: dict, context: dict) -> None:
        """Process the products record.

        Args:
            record: Individual record in the stream.
            context: Stream partition or context dictionary.
        """
        product_data = {
            "code": record.get("code"),
            "name": record.get("name"),
            "maker": record.get("maker"),
            "sku": record.get("sku"),
            "barcode": record.get("barcode"),
            "ncm": record.get("ncm"),
            "description": record.get("description"),
            "observation": record.get("observation"),
            "line": record.get("line"),
            "active": record.get("active", True)
        }
        self.make_request("products", product_data)


class PricesSink(SharpiBaseSink):
    """Sharpi prices sink class."""

    def process_record(self, record: dict, context: dict) -> None:
        """Process the prices record.

        Args:
            record: Individual record in the stream.
            context: Stream partition or context dictionary.
        """
        price_data = {
            "product_code": record.get("product_code"),
            "price_table_id": record.get("price_table_id"),
            "price": str(record.get("price")) if record.get("price") is not None else None,
            "max_allowed_discount": str(record.get("max_allowed_discount")) if record.get("max_allowed_discount") is not None else None,
            "discount_type": record.get("discount_type", "percentage"),
            "active": record.get("active", True),
            "custom_attributes": record.get("custom_attributes", {})
        }
        self.make_request("prices", price_data)


class CustomersSink(SharpiBaseSink):
    """Sharpi customers sink class."""

    def process_record(self, record: dict, context: dict) -> None:
        """Process the customers record.

        Args:
            record: Individual record in the stream.
            context: Stream partition or context dictionary.
        """
        customer_data = {
            "code": record.get("code"),
            "name": record.get("name"),
            "legal_name": record.get("legal_name"),
            "email": record.get("email"),
            "billing_address": {
                "street": record.get("billing_address", {}).get("street"),
                "city": record.get("billing_address", {}).get("city"),
                "state": record.get("billing_address", {}).get("state"),
                "zip": record.get("billing_address", {}).get("zip"),
                "country": record.get("billing_address", {}).get("country"),
                "full_address": record.get("billing_address", {}).get("full_address"),
                "custom_attributes": record.get("billing_address", {}).get(
                    "custom_attributes", {}
                )
            },
            "shipping_address": {
                "street": record.get("shipping_address", {}).get("street"),
                "city": record.get("shipping_address", {}).get("city"),
                "state": record.get("shipping_address", {}).get("state"),
                "zip": record.get("shipping_address", {}).get("zip"),
                "country": record.get("shipping_address", {}).get("country"),
                "full_address": record.get("shipping_address", {}).get("full_address"),
                "custom_attributes": record.get("shipping_address", {}).get(
                    "custom_attributes", {}
                )
            },
            "tax_id": record.get("tax_id"),
            "active": record.get("active", True),
            "default_price_list_id": record.get("default_price_list_id"),
            "salesperson_ids": record.get("salesperson_ids", []),
            "custom_attributes": record.get("custom_attributes", {})
        }
        self.make_request("customers", customer_data)


# Keep the old SharpiSink for backward compatibility
class SharpiSink(SharpiBaseSink):
    """Sharpi target sink class."""

    def process_record(self, record: dict, context: dict) -> None:
        raise NotImplementedError