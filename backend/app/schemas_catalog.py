"""Product catalog schemas — exposes plan_type templates with country + rotation_mode choices."""

from typing import Optional

from pydantic import BaseModel, Field


class ProductVariant(BaseModel):
    """A specific configuration: plan_type + location + rotation_mode + price."""

    plan_code: str
    plan_type: str  # residential | mobile | datacenter | isp
    country: str  # ISO alpha-2 (US, GB, NG, etc.)
    rotation_mode: str  # rotating | static
    price_ngn: float  # static mode includes multiplier
    quantity: int  # GB
    duration_days: int
    features: list[str]
    in_stock: bool = True  # false if Rayobyte pool is exhausted for this combo


class ProductCity(BaseModel):
    """City picker item for residential/mobile plans."""
    id: int
    city_name: str
    state_code: Optional[str] = None
    isp_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ProductTemplate(BaseModel):
    """A plan_type template — customer picks location + rotation_mode from these choices."""

    plan_type: str
    rotation_mode_options: list[str]  # ['rotating', 'static'] or just one
    available_countries: list[str]  # ['US', 'GB', 'DE', ...] what we support
    base_quantity_gb: int
    base_price_ngn: float  # legacy per-IP price (DC/ISP)
    base_price_per_gb: Optional[float] = None  # per-GB price (residential/mobile)
    base_price_per_ip: Optional[float] = None  # per-IP price (DC/ISP)
    min_gb: Optional[int] = None  # minimum GB customer can buy (residential/mobile)
    max_gb: Optional[int] = None  # maximum GB customer can buy
    gb_tiers: Optional[list[int]] = None  # suggested GB tiers (e.g. [5, 10, 20, 50])
    supports_city: bool = False  # residential/mobile only
    cities: dict[str, list[ProductCity]] = {}  # country_code -> list of cities
    duration_days: int
    static_price_multiplier: float
    supports_country_change: bool  # false for datacenter/isp (fixed per IP)
    description: str
    variants: list[ProductVariant] = []  # all combinations we offer


class ProductTemplatesResponse(BaseModel):
    """Catalog response — list of plan_type templates."""

    templates: list[ProductTemplate]
    countries_supported: list[str]  # all unique countries across templates
    rotation_modes_supported: list[str]  # ['rotating', 'static']


class OrderCreateRequest(BaseModel):
    """Customer creates a new order — picks plan_type + country + city + GB + rotation_mode."""

    plan_type: str = Field(..., description="residential | mobile | datacenter | isp")
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2")
    rotation_mode: str = Field(default="rotating", description="rotating | static")
    quantity_gb: Optional[int] = Field(None, description="GB to purchase (residential/mobile). null = plan default.")
    duration_days: Optional[int] = Field(None, description="Override duration; null = plan default")
    payment_reference: Optional[str] = Field(None, description="Flutterwave tx_ref if pre-paid")
    # Sprint 13 — city picker (residential/mobile only)
    city_id: Optional[int] = Field(
        None,
        description="City ID for residential/mobile orders. None = random (country pool).",
    )
    city_name: Optional[str] = Field(None, description="City name for cred provisioning (denormalized).")


class OrderCreateResponse(BaseModel):
    """Order creation response with SOCKS5 connection details."""

    order_id: str
    plan_type: str
    country: str
    rotation_mode: str
    quantity_gb: int
    duration_days: int
    amount_paid_ngn: float
    status: str

    # Connection details (same shape as ProxyFullDetails so customer can copy/paste)
    styxproxy_username: str
    styxproxy_password: str  # plaintext — store now, shown once
    proxy_host: str = "proxy.styxproxy.com"
    proxy_port_socks5: int = 1080
    proxy_port_http: int = 8080
    protocol: str = "socks5"

    expires_at: Optional[str] = None  # ISO datetime

    # Ready-to-use connection examples
    curl_socks5_example: str
    curl_http_example: str
    python_socks5_example: str

    # For static mode: the assigned IP (we pre-pick one from Rayobyte pool)
    assigned_static_ip: Optional[str] = None

    # What to do next
    next_steps: list[str] = [
        "Save your password now — it will only be shown once.",
        "Connect via SOCKS5: see the curl/python examples below.",
        "Manage your proxy at /manage: change location, rotate password, view usage.",
    ]