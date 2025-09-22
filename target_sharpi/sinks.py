"""Sharpi target sink class, which handles writing streams."""

from __future__ import annotations
from ast import literal_eval
import backoff
import requests
from typing import Any
from singer_sdk.sinks import RecordSink
from singer_sdk.exceptions import RetriableAPIError


class DuplicatedRecordError(Exception):
    """Exception raised when a duplicated record is found."""


def _encode_everything(input: Any) -> Any:
    if isinstance(input, str):
        return _encode_back(input)
    elif isinstance(input, dict):
        return {k: _encode_everything(v) for k, v in input.items()}
    elif isinstance(input, list):
        return [_encode_everything(v) for v in input]

    return input


def _encode_back(text: str) -> str:
    """Safely handle text encoding to ensure proper UTF-8 strings."""
    if not isinstance(text, str):
        return text

    try:
        return text.encode("utf-8")
    except UnicodeEncodeError:
        pass

    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    try:
        return text.encode("utf-8", errors="replace").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


class SharpiBaseSink(RecordSink):
    """Base Sharpi target sink class."""

    def _parse_custom_attributes(self, custom_attrs):
        """Parse custom attributes from various formats."""
        if isinstance(custom_attrs, dict):
            return custom_attrs
        elif isinstance(custom_attrs, str):
            if not custom_attrs or custom_attrs == "None":
                return {}
            try:
                return literal_eval(custom_attrs)
            except (ValueError, SyntaxError):
                # If literal_eval fails, try to return as is or empty dict
                return {}
        else:
            return {}

    @property
    def key_properties(self) -> list[str]:
        """Get key properties for the sink."""
        return []

    @property
    def api_key(self) -> str:
        """Get API key from config."""
        return self.config["api_key"]

    @property
    def base_url(self) -> str:
        """Get base URL for Sharpi API."""
        return "https://api.sharpi.com.br/v1/partner"

    @backoff.on_exception(backoff.expo, RetriableAPIError, max_time=60)
    def make_request(self, endpoint: str, data: dict[str, Any], method: str = "POST") -> None:
        """Make HTTP request to Sharpi API."""
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }

        self.logger.info("Making request to %s", url)
        self.logger.debug("Request data: %s", data)

        response = requests.request(method, url, json=data, headers=headers)

        self.logger.info("Request body: %s", data)
        self.logger.info("Response status code: %s", response.status_code)
        self.logger.debug("Response: %s", response.text)

        if response.status_code == 400:
            response_json = response.json()
            if "duplicate key" in response_json.get("message", "") or "already exists" in response_json.get("message", ""):
                self.logger.warning("Duplicate record found for %s: %s", endpoint, data.get("code", "unknown"))
                raise DuplicatedRecordError(response_json.get("message"))

            self.logger.warning("Response: %s", response_json)
            response.raise_for_status()

        if response.status_code > 499:
            self.logger.error("Server error: %s - %s", response.status_code, response.text)
            raise RetriableAPIError(response.text)


class ProductsSink(SharpiBaseSink):
    """Sharpi products sink class."""

    @property
    def key_properties(self) -> list[str]:
        """Get key properties for the sink."""
        return ["code"]

    def process_record(self, record: dict, context: dict) -> None:
        """Process the products record.

        Args:
            record: Individual record in the stream.
            context: Stream partition or context dictionary.
        """
        product_data = {
            "code": str(record.get("code")),
            "name": record.get("name"),
            "maker": record.get("maker"),
            "sku": record.get("sku"),
            "barcode": record.get("barcode"),
            "ncm": record.get("ncm"),
            "description": record.get("description"),
            "observation": record.get("observation"),
            "line": record.get("line"),
            "active": record.get("active", True),
            "custom_attributes": self._parse_custom_attributes(record.get("custom_attributes", {}))
        }
        product_data = _encode_everything(product_data)

        try:
            self.make_request("products", product_data)
        except DuplicatedRecordError as e:
            self.make_request(
                f"products/{record.get('code')}",
                product_data,
                method="PATCH"
            )
            self.logger.warning("Duplicated record patched for %s: %s", record.get("code"), e)
            return


class PricesSink(SharpiBaseSink):
    """Sharpi prices sink class."""

    @property
    def key_properties(self) -> list[str]:
        """Get key properties for the sink."""
        return ["product_code"]

    def process_record(self, record: dict, context: dict) -> None:
        """Process the prices record.

        Args:
            record: Individual record in the stream.
            context: Stream partition or context dictionary.
        """
        price_data = {
            "product_code": record.get("product_code"),
            "product_unit_id": record.get("product_unit_id", ""),
            "price_table_id": record.get("price_table_id"),
            "price": str(
                record.get("price")
            ) if record.get("price") is not None else None,
            "max_allowed_discount": str(
                record.get("max_allowed_discount")
            ) if record.get("max_allowed_discount") is not None else None,
            "discount_type": record.get("discount_type", "percentage"),
            "active": record.get("active", True),
            "custom_attributes": self._parse_custom_attributes(record.get("custom_attributes", {}))
        }
        price_data = _encode_everything(price_data)

        try:
            self.make_request("prices", price_data)
        except DuplicatedRecordError as e:
            # Build the PATCH URL with all unique key components
            product_unit_id = record.get('product_unit_id', '')
            patch_url = f"prices/{record.get('price_table_id')}/{record.get('product_code')}"
            if product_unit_id:
                patch_url += f"/{product_unit_id}"

            self.make_request(
                patch_url,
                price_data,
                method="PATCH"
            )
            self.logger.warning("Duplicated record patched for product_code=%s, product_unit_id=%s: %s",
                              record.get("product_code"), product_unit_id, e)
            return


class CustomersSink(SharpiBaseSink):
    """Sharpi customers sink class."""

    @property
    def key_properties(self) -> list[str]:
        """Get key properties for the sink."""
        return ["code"]

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
                "custom_attributes": literal_eval(record.get("billing_address", {}).get(
                    "custom_attributes", {}
                ))
            },
            "shipping_address": {
                "street": record.get("shipping_address", {}).get("street"),
                "city": record.get("shipping_address", {}).get("city"),
                "state": record.get("shipping_address", {}).get("state"),
                "zip": record.get("shipping_address", {}).get("zip"),
                "country": record.get("shipping_address", {}).get("country"),
                "full_address": record.get("shipping_address", {}).get("full_address"),
                "custom_attributes": literal_eval(record.get("shipping_address", {}).get(
                    "custom_attributes", {}
                ))
            },
            "tax_id": record.get("tax_id"),
            "active": record.get("active", True),
            "default_price_list_id": record.get("default_price_list_id"),
            "salesperson_ids": record.get("salesperson_ids", []),
            "custom_attributes": self._parse_custom_attributes(record.get("custom_attributes", {}))
        }
        customer_data = _encode_everything(customer_data)

        try:
            self.make_request("customers", customer_data)
        except DuplicatedRecordError as e:
            self.make_request(
                f"customers/{record.get('code')}",
                customer_data,
                method="PATCH"
            )
            self.logger.warning("Duplicated record patched for %s: %s", record.get("code"), e)
            return


# Keep the old SharpiSink for backward compatibility
class SharpiSink(SharpiBaseSink):
    """Sharpi target sink class."""

    def process_record(self, record: dict, context: dict) -> None:
        """Process the record. Not implemented.

        Args:
            record: Individual record in the stream.
            context: Stream partition or context dictionary.
        """
        raise NotImplementedError("SharpiSink is not implemented")