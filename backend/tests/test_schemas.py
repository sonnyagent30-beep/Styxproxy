"""Tests for schemas module."""
import pytest
from pydantic import ValidationError
from app.schemas import (
    validate_phone,
    validate_country,
    PlatformRegisterRequest,
    OrderCreateRequest,
    PaymentInitiateRequest,
    AdminBlockRequest,
    FlutterwaveWebhookPayload,
    ErrorResponse,
)


class TestValidatePhone:
    def test_valid_with_plus(self):
        assert validate_phone("+2348012345678") == "+2348012345678"

    def test_valid_without_plus(self):
        assert validate_phone("2348012345678") == "2348012345678"

    def test_valid_10_digit_no_prefix(self):
        assert validate_phone("08012345678") == "08012345678"

    def test_invalid_too_short(self):
        with pytest.raises(ValueError):
            validate_phone("12345")

    def test_invalid_too_long(self):
        with pytest.raises(ValueError):
            validate_phone("234" + "1" * 20)

    def test_invalid_with_letters(self):
        with pytest.raises(ValueError):
            validate_phone("+2348012345ABC")

    def test_invalid_empty(self):
        with pytest.raises(ValueError):
            validate_phone("")


class TestValidateCountry:
    def test_valid_ng(self):
        assert validate_country("NG") == "NG"

    def test_valid_uk(self):
        assert validate_country("UK") == "UK"

    def test_valid_us(self):
        assert validate_country("US") == "US"

    def test_valid_lowercase(self):
        assert validate_country("ng") == "NG"

    def test_invalid_code(self):
        with pytest.raises(ValueError):
            validate_country("XX")

    def test_invalid_empty(self):
        with pytest.raises(ValueError):
            validate_country("")

    def test_invalid_three_letters(self):
        with pytest.raises(ValueError):
            validate_country("NGA")


class TestPlatformRegisterRequest:
    def test_create_with_valid_data(self):
        req = PlatformRegisterRequest(phone="+2348012345678", name="Test User")
        assert req.phone == "+2348012345678"
        assert req.name == "Test User"

    def test_create_with_platform(self):
        req = PlatformRegisterRequest(phone="+2348012345678", platform="whatsapp")
        assert req.platform == "whatsapp"

    def test_optional_metadata(self):
        req = PlatformRegisterRequest(phone="+2348012345678", metadata={"key": "value"})
        assert req.metadata == {"key": "value"}

    def test_phone_validation(self):
        with pytest.raises(ValidationError):
            PlatformRegisterRequest(phone="123")

    def test_platform_default(self):
        req = PlatformRegisterRequest(phone="+2348012345678")
        assert req.platform == "whatsapp"


class TestOrderCreateRequest:
    def test_valid_request(self):
        req = OrderCreateRequest(plan_code="ISP-NG-1", country="NG", quantity=1)
        assert req.plan_code == "ISP-NG-1"
        assert req.country == "NG"
        assert req.quantity == 1

    def test_country_validation(self):
        with pytest.raises(ValidationError):
            OrderCreateRequest(plan_code="ISP-NG-1", country="XX", quantity=1)

    def test_quantity_default(self):
        req = OrderCreateRequest(plan_code="ISP-NG-1", country="NG")
        assert req.quantity == 1

    def test_quantity_custom(self):
        req = OrderCreateRequest(plan_code="ISP-NG-1", country="NG", quantity=5)
        assert req.quantity == 5

    def test_plan_code_required(self):
        with pytest.raises(ValidationError):
            OrderCreateRequest(country="NG", quantity=1)

    def test_optional_callback_url(self):
        req = OrderCreateRequest(
            plan_code="ISP-NG-1",
            country="NG",
            callback_url="https://example.com/callback",
        )
        assert req.callback_url == "https://example.com/callback"


class TestPaymentInitiateRequest:
    def test_valid_phone_with_prefix(self):
        req = PaymentInitiateRequest(plan_code="ISP-NG-1", customer_phone="+2348012345678", quantity=1)
        assert req.customer_phone == "+2348012345678"

    def test_valid_phone_no_prefix(self):
        req = PaymentInitiateRequest(plan_code="ISP-NG-1", customer_phone="08012345678", quantity=1)
        assert req.customer_phone == "08012345678"

    def test_invalid_phone_raises(self):
        with pytest.raises(ValidationError):
            PaymentInitiateRequest(plan_code="ISP-NG-1", customer_phone="invalid", quantity=1)

    def test_plan_code_required(self):
        with pytest.raises(ValidationError):
            PaymentInitiateRequest(customer_phone="+2348012345678", quantity=1)

    def test_customer_phone_required(self):
        with pytest.raises(ValidationError):
            PaymentInitiateRequest(plan_code="ISP-NG-1", quantity=1)

    def test_quantity_default(self):
        req = PaymentInitiateRequest(plan_code="ISP-NG-1", customer_phone="+2348012345678")
        assert req.quantity == 1

    def test_quantity_custom(self):
        req = PaymentInitiateRequest(plan_code="ISP-NG-1", customer_phone="+2348012345678", quantity=3)
        assert req.quantity == 3

    def test_optional_callback_url(self):
        req = PaymentInitiateRequest(
            plan_code="ISP-NG-1",
            customer_phone="+2348012345678",
            callback_url="https://example.com/callback",
        )
        assert req.callback_url is not None


class TestAdminBlockRequest:
    def test_create_with_reason(self):
        req = AdminBlockRequest(reason="Abuse")
        assert req.reason == "Abuse"

    def test_reason_required(self):
        with pytest.raises(ValidationError):
            AdminBlockRequest()

    def test_reason_max_length(self):
        with pytest.raises(ValidationError):
            AdminBlockRequest(reason="x" * 501)

    def test_reason_at_max_length(self):
        req = AdminBlockRequest(reason="x" * 500)
        assert len(req.reason) == 500


class TestFlutterwaveWebhookPayload:
    def test_create_with_event_and_data(self):
        payload = FlutterwaveWebhookPayload(event="charge.completed", data={"tx_ref": "TXF-123"})
        assert payload.event == "charge.completed"
        assert payload.data["tx_ref"] == "TXF-123"

    def test_event_required(self):
        with pytest.raises(ValidationError):
            FlutterwaveWebhookPayload(data={})

    def test_data_required(self):
        with pytest.raises(ValidationError):
            FlutterwaveWebhookPayload(event="charge.completed")

    def test_data_dict_type(self):
        payload = FlutterwaveWebhookPayload(event="charge.completed", data={"amount": 5000})
        assert isinstance(payload.data, dict)

    def test_with_nested_data(self):
        payload = FlutterwaveWebhookPayload(
            event="charge.completed",
            data={"customer": {"email": "test@example.com", "phone_number": "+2348012345678"}},
        )
        assert payload.data["customer"]["email"] == "test@example.com"


class TestErrorResponse:
    def test_create_with_error_dict(self):
        resp = ErrorResponse(error={"code": "INVALID_PLAN", "message": "Plan not found"})
        assert resp.error["code"] == "INVALID_PLAN"

    def test_error_required(self):
        with pytest.raises(ValidationError):
            ErrorResponse()

    def test_error_dict_type(self):
        resp = ErrorResponse(error={"detail": "Something went wrong"})
        assert isinstance(resp.error, dict)

    def test_with_nested_error_details(self):
        resp = ErrorResponse(
            error={
                "code": "VALIDATION_ERROR",
                "details": [{"field": "phone", "issue": "invalid format"}],
            }
        )
        assert resp.error["details"][0]["field"] == "phone"

    def test_with_simple_message(self):
        resp = ErrorResponse(error={"detail": "Order not found"})
        assert resp.error["detail"] == "Order not found"
