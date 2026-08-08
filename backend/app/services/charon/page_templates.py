"""Page-aware prompt templates for Charon.

This module provides context-specific system prompt additions based on which
page the user is viewing in the Styxproxy website. This enables Charon to give
more relevant, contextual responses.

Usage:
    from app.services.charon.page_templates import get_page_prompt_addition
    
    prompt_addition = get_page_prompt_addition(page_context)
    # Append to existing system prompt
"""

from typing import Any

# Plan details mapping for product detail pages
PLAN_DETAILS = {
    "ISP-UK": {
        "price": "₦6,500/mo",
        "data": "Dedicated",
        "use_cases": "business applications, stable IP for banking, corporate VPN",
        "speed": "10Mbps guaranteed",
    },
    "ISP-US": {
        "price": "₦6,500/mo",
        "data": "Dedicated",
        "use_cases": "US-based services, American streaming, business applications",
        "speed": "10Mbps guaranteed",
    },
    "ISP-DE": {
        "price": "₦7,500/mo",
        "data": "Dedicated",
        "use_cases": "EU services, German banking, European streaming",
        "speed": "10Mbps guaranteed",
    },
    "RESI-US-20GB": {
        "price": "₦15,000/mo",
        "data": "20GB",
        "use_cases": "sneaker sites, ticket purchasing, social media management, general browsing",
        "speed": "Best effort, typically 5-20Mbps",
    },
    "RESI-UK-20GB": {
        "price": "₦15,000/mo",
        "data": "20GB",
        "use_cases": "UK streaming, British banking sites, UK-specific services",
        "speed": "Best effort, typically 5-20Mbps",
    },
    "DC-US-20GB": {
        "price": "₦8,000/mo",
        "data": "20GB",
        "use_cases": "web scraping, automation, server hosting, API calls",
        "speed": "100Mbps shared",
    },
    "DC-EU-20GB": {
        "price": "₦8,000/mo",
        "data": "20GB",
        "use_cases": "EU web scraping, European automation, server hosting",
        "speed": "100Mbps shared",
    },
}


def get_page_prompt_addition(page_context: dict[str, Any] | None) -> str:
    """Get the appropriate system prompt addition based on page context.
    
    Args:
        page_context: Dictionary containing page_type and any relevant context
                     like plan_code, post_title, etc.
    
    Returns:
        A string to append to the system prompt, or empty string if no
        page context is provided.
    """
    if not page_context:
        return ""
    
    page_type = page_context.get("page_type")
    
    if page_type == "pricing":
        return _get_pricing_template()
    elif page_type == "product_detail":
        return _get_product_detail_template(page_context)
    elif page_type == "blog_post":
        return _get_blog_post_template(page_context)
    elif page_type in ("checkout", "receipt"):
        return _get_checkout_template()
    
    return ""


def _get_pricing_template() -> str:
    """System prompt addition for pricing page visitors."""
    return (
        "[System prompt addition for pricing page visitors]\n"
        "The customer is currently viewing our pricing page. Available plans:\n"
        "- ISP (dedicated): UK ₦6,500/mo, US ₦6,500/mo, DE ₦7,500/mo\n"
        "- Residential: ₦15,000/mo for 20GB\n"
        "- Datacenter: ₦8,000/mo for 20GB\n"
        "Lead with plan specifics, not generic explanations. If they ask about speed, "
        "mention our SLA. If they ask about Nigeria compatibility, mention the Nigerian banking sites we support."
    )


def _get_product_detail_template(page_context: dict[str, Any]) -> str:
    """System prompt addition for product detail page visitors."""
    plan_code = page_context.get("plan_code", "")
    details = PLAN_DETAILS.get(plan_code, {})
    
    if not details:
        return ""
    
    return (
        "[System prompt addition for product detail page]\n"
        f"Customer is viewing {plan_code}. Key facts to reference:\n"
        f"- Price: {details.get('price', 'N/A')}\n"
        f"- Data allowance: {details.get('data', 'N/A')}\n"
        f"- Use cases: {details.get('use_cases', 'general browsing')}\n"
        f"- Speed SLA: {details.get('speed', 'standard')}\n"
        'If they ask "is this good for X?", answer definitively about that plan.'
    )


def _get_blog_post_template(page_context: dict[str, Any]) -> str:
    """System prompt addition for blog post readers."""
    post_title = page_context.get("post_title", "Untitled Post")
    topics = page_context.get("topics", "general topics")
    
    return (
        "[System prompt addition for blog readers]\n"
        f'Customer is reading our blog post "{post_title}". This post covers: {topics}.\n'
        "Use it as the primary reference. Quote from it if relevant. "
        "Link to it if the customer asks a follow-up."
    )


def _get_checkout_template() -> str:
    """System prompt addition for checkout/receipt pages."""
    return (
        "[System prompt addition for checkout/receipt page]\n"
        "Customer is in the checkout flow or has just completed a purchase.\n"
        "- Be helpful but NOT pushy. Don't hard-sell.\n"
        "- If they have a tx_ref in context, you can look up their order.\n"
        "- If they're asking about payment, direct them to Flutterwave's support.\n"
        "- Never ask for payment details — we never store them."
    )
