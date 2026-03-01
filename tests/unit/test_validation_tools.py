"""Unit tests for validation tools."""

import pytest

from support_bot.tools.validation_tools import validate_email, validate_order_number


class TestValidateOrderNumber:
    def test_valid_alphanumeric_6(self):
        result = validate_order_number("ABC123")
        assert result["valid"] is True

    def test_valid_alphanumeric_12(self):
        result = validate_order_number("ABCDEF123456")
        assert result["valid"] is True

    def test_valid_digits_only(self):
        result = validate_order_number("123456")
        assert result["valid"] is True

    def test_valid_letters_only(self):
        result = validate_order_number("ABCDEFGH")
        assert result["valid"] is True

    def test_lowercase_input_accepted(self):
        result = validate_order_number("abc123")
        assert result["valid"] is True
        assert "ABC123" in result["message"]

    def test_leading_trailing_spaces(self):
        result = validate_order_number("  ABC123  ")
        assert result["valid"] is True

    def test_too_short(self):
        result = validate_order_number("AB123")
        assert result["valid"] is False
        assert "invalid" in result["message"].lower()

    def test_too_long(self):
        result = validate_order_number("ABCDEFGHIJKLM")
        assert result["valid"] is False

    def test_special_chars(self):
        result = validate_order_number("ABC-12345")
        assert result["valid"] is False

    def test_spaces_in_number(self):
        result = validate_order_number("ABC 123")
        assert result["valid"] is False

    def test_empty_string(self):
        result = validate_order_number("")
        assert result["valid"] is False

    def test_exactly_6_chars(self):
        result = validate_order_number("AAAAAA")
        assert result["valid"] is True

    def test_exactly_12_chars(self):
        result = validate_order_number("AAAAAAAAAAAA")
        assert result["valid"] is True

    def test_13_chars_invalid(self):
        result = validate_order_number("AAAAAAAAAAAAA")
        assert result["valid"] is False


class TestValidateEmail:
    def test_valid_simple(self):
        result = validate_email("user@example.com")
        assert result["valid"] is True

    def test_valid_subdomain(self):
        result = validate_email("user@mail.example.com")
        assert result["valid"] is True

    def test_valid_plus_address(self):
        result = validate_email("user+tag@example.com")
        assert result["valid"] is True

    def test_valid_dots_in_local(self):
        result = validate_email("first.last@example.com")
        assert result["valid"] is True

    def test_valid_dashes(self):
        result = validate_email("first-last@my-domain.org")
        assert result["valid"] is True

    def test_missing_at(self):
        result = validate_email("userexample.com")
        assert result["valid"] is False

    def test_missing_domain(self):
        result = validate_email("user@")
        assert result["valid"] is False

    def test_missing_tld(self):
        result = validate_email("user@example")
        assert result["valid"] is False

    def test_empty_string(self):
        result = validate_email("")
        assert result["valid"] is False

    def test_spaces_invalid(self):
        result = validate_email("user @example.com")
        assert result["valid"] is False

    def test_double_at(self):
        result = validate_email("user@@example.com")
        assert result["valid"] is False

    def test_valid_with_whitespace_trimmed(self):
        result = validate_email("  user@example.com  ")
        assert result["valid"] is True
