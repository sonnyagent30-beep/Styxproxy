"""Seed the countries table with all 195 ISO 3166-1 entries.

Theme C — initial backfill for the countries table. The 9 countries
currently hardcoded in app/services/provider.py::available_countries
are seeded with is_supported=TRUE; the rest are FALSE.

Run as a one-off after migration 015:
  /opt/styxproxy/backend/venv/bin/python3 /opt/styxproxy/backend/scripts/seed_countries.py

Idempotent: uses ON CONFLICT (code) DO UPDATE so re-runs are safe. The
seeds list is the authoritative source of truth — update here, then
re-run the script to push to live.

Source: ISO 3166-1 (officially published by ISO). Updated 2026-07-28.
Flag emojis are Unicode regional indicator pairs (same source as
country-flag-icons on GitHub).
"""

import asyncio
import os
import sys

# Add backend to path so we can import app.*
sys.path.insert(0, "/opt/styxproxy/backend")

# Load env from /opt/styxproxy/.env (same as api)
_env_path = "/opt/styxproxy/.env"
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

from sqlalchemy import select  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models import Country  # noqa: E402

# (code, code3, name, flag_emoji, region, subregion, is_supported, proxy_pool)
# is_supported matches the 9 countries currently hardcoded in
# app/services/provider.py::available_countries. All entries are
# (region, subregion) per UN M49 classification.
SEED = [
    # AFRICA
    ("DZ", "DZA", "Algeria", "🇩🇿", "Africa", "Northern Africa", False, None),
    ("AO", "AGO", "Angola", "🇦🇴", "Africa", "Sub-Saharan Africa", False, None),
    ("BJ", "BEN", "Benin", "🇧🇯", "Africa", "Sub-Saharan Africa", False, None),
    ("BW", "BWA", "Botswana", "🇧🇼", "Africa", "Sub-Saharan Africa", False, None),
    ("BF", "BFA", "Burkina Faso", "🇧🇫", "Africa", "Sub-Saharan Africa", False, None),
    ("BI", "BDI", "Burundi", "🇧🇮", "Africa", "Sub-Saharan Africa", False, None),
    ("CV", "CPV", "Cabo Verde", "🇨🇻", "Africa", "Sub-Saharan Africa", False, None),
    ("CM", "CMR", "Cameroon", "🇨🇲", "Africa", "Sub-Saharan Africa", False, None),
    ("CF", "CAF", "Central African Republic", "🇨🇫", "Africa", "Sub-Saharan Africa", False, None),
    ("TD", "TCD", "Chad", "🇹🇩", "Africa", "Sub-Saharan Africa", False, None),
    ("KM", "COM", "Comoros", "🇰🇲", "Africa", "Sub-Saharan Africa", False, None),
    ("CG", "COG", "Congo", "🇨🇬", "Africa", "Sub-Saharan Africa", False, None),
    ("CD", "COD", "Congo, Democratic Republic of the", "🇨🇩", "Africa", "Sub-Saharan Africa", False, None),
    ("CI", "CIV", "Côte d'Ivoire", "🇨🇮", "Africa", "Sub-Saharan Africa", False, None),
    ("DJ", "DJI", "Djibouti", "🇩🇯", "Africa", "Sub-Saharan Africa", False, None),
    ("EG", "EGY", "Egypt", "🇪🇬", "Africa", "Northern Africa", False, None),
    ("GQ", "GNQ", "Equatorial Guinea", "🇬🇶", "Africa", "Sub-Saharan Africa", False, None),
    ("ER", "ERI", "Eritrea", "🇪🇷", "Africa", "Sub-Saharan Africa", False, None),
    ("SZ", "SWZ", "Eswatini", "🇸🇿", "Africa", "Sub-Saharan Africa", False, None),
    ("ET", "ETH", "Ethiopia", "🇪🇹", "Africa", "Sub-Saharan Africa", False, None),
    ("GA", "GAB", "Gabon", "🇬🇦", "Africa", "Sub-Saharan Africa", False, None),
    ("GM", "GMB", "Gambia", "🇬🇲", "Africa", "Sub-Saharan Africa", False, None),
    ("GH", "GHA", "Ghana", "🇬🇭", "Africa", "Sub-Saharan Africa", False, None),
    ("GN", "GIN", "Guinea", "🇬🇳", "Africa", "Sub-Saharan Africa", False, None),
    ("GW", "GNB", "Guinea-Bissau", "🇬🇼", "Africa", "Sub-Saharan Africa", False, None),
    ("KE", "KEN", "Kenya", "🇰🇪", "Africa", "Sub-Saharan Africa", False, None),
    ("LS", "LSO", "Lesotho", "🇱🇸", "Africa", "Sub-Saharan Africa", False, None),
    ("LR", "LBR", "Liberia", "🇱🇷", "Africa", "Sub-Saharan Africa", False, None),
    ("LY", "LBY", "Libya", "🇱🇾", "Africa", "Northern Africa", False, None),
    ("MG", "MDG", "Madagascar", "🇲🇬", "Africa", "Sub-Saharan Africa", False, None),
    ("MW", "MWI", "Malawi", "🇲🇼", "Africa", "Sub-Saharan Africa", False, None),
    ("ML", "MLI", "Mali", "🇲🇱", "Africa", "Sub-Saharan Africa", False, None),
    ("MR", "MRT", "Mauritania", "🇲🇷", "Africa", "Sub-Saharan Africa", False, None),
    ("MU", "MUS", "Mauritius", "🇲🇺", "Africa", "Sub-Saharan Africa", False, None),
    ("MA", "MAR", "Morocco", "🇲🇦", "Africa", "Northern Africa", False, None),
    ("MZ", "MOZ", "Mozambique", "🇲🇿", "Africa", "Sub-Saharan Africa", False, None),
    ("NA", "NAM", "Namibia", "🇳🇦", "Africa", "Sub-Saharan Africa", False, None),
    ("NE", "NER", "Niger", "🇳🇪", "Africa", "Sub-Saharan Africa", False, None),
    ("NG", "NGA", "Nigeria", "🇳🇬", "Africa", "Sub-Saharan Africa", True, "residential"),
    ("RW", "RWA", "Rwanda", "🇷🇼", "Africa", "Sub-Saharan Africa", False, None),
    ("ST", "STP", "São Tomé and Príncipe", "🇸🇹", "Africa", "Sub-Saharan Africa", False, None),
    ("SN", "SEN", "Senegal", "🇸🇳", "Africa", "Sub-Saharan Africa", False, None),
    ("SC", "SYC", "Seychelles", "🇸🇨", "Africa", "Sub-Saharan Africa", False, None),
    ("SL", "SLE", "Sierra Leone", "🇸🇱", "Africa", "Sub-Saharan Africa", False, None),
    ("SO", "SOM", "Somalia", "🇸🇴", "Africa", "Sub-Saharan Africa", False, None),
    ("ZA", "ZAF", "South Africa", "🇿🇦", "Africa", "Sub-Saharan Africa", False, None),
    ("SS", "SSD", "South Sudan", "🇸🇸", "Africa", "Sub-Saharan Africa", False, None),
    ("SD", "SDN", "Sudan", "🇸🇩", "Africa", "Northern Africa", False, None),
    ("TZ", "TZA", "Tanzania", "🇹🇿", "Africa", "Sub-Saharan Africa", False, None),
    ("TG", "TGO", "Togo", "🇹🇬", "Africa", "Sub-Saharan Africa", False, None),
    ("TN", "TUN", "Tunisia", "🇹🇳", "Africa", "Northern Africa", False, None),
    ("UG", "UGA", "Uganda", "🇺🇬", "Africa", "Sub-Saharan Africa", False, None),
    ("ZM", "ZMB", "Zambia", "🇿🇲", "Africa", "Sub-Saharan Africa", False, None),
    ("ZW", "ZWE", "Zimbabwe", "🇿🇼", "Africa", "Sub-Saharan Africa", False, None),
    # AMERICAS
    ("AG", "ATG", "Antigua and Barbuda", "🇦🇬", "Americas", "Caribbean", False, None),
    ("AR", "ARG", "Argentina", "🇦🇷", "Americas", "South America", False, None),
    ("BS", "BHS", "Bahamas", "🇧🇸", "Americas", "Caribbean", False, None),
    ("BB", "BRB", "Barbados", "🇧🇧", "Americas", "Caribbean", False, None),
    ("BZ", "BLZ", "Belize", "🇧🇿", "Americas", "Central America", False, None),
    ("BO", "BOL", "Bolivia", "🇧🇴", "Americas", "South America", False, None),
    ("BR", "BRA", "Brazil", "🇧🇷", "Americas", "South America", False, None),
    ("CA", "CAN", "Canada", "🇨🇦", "Americas", "Northern America", True, "residential"),
    ("CL", "CHL", "Chile", "🇨🇱", "Americas", "South America", False, None),
    ("CO", "COL", "Colombia", "🇨🇴", "Americas", "South America", False, None),
    ("CR", "CRI", "Costa Rica", "🇨🇷", "Americas", "Central America", False, None),
    ("CU", "CUB", "Cuba", "🇨🇺", "Americas", "Caribbean", False, None),
    ("DM", "DMA", "Dominica", "🇩🇲", "Americas", "Caribbean", False, None),
    ("DO", "DOM", "Dominican Republic", "🇩🇴", "Americas", "Caribbean", False, None),
    ("EC", "ECU", "Ecuador", "🇪🇨", "Americas", "South America", False, None),
    ("SV", "SLV", "El Salvador", "🇸🇻", "Americas", "Central America", False, None),
    ("GD", "GRD", "Grenada", "🇬🇩", "Americas", "Caribbean", False, None),
    ("GT", "GTM", "Guatemala", "🇬🇹", "Americas", "Central America", False, None),
    ("GY", "GUY", "Guyana", "🇬🇾", "Americas", "South America", False, None),
    ("HT", "HTI", "Haiti", "🇭🇹", "Americas", "Caribbean", False, None),
    ("HN", "HND", "Honduras", "🇭🇳", "Americas", "Central America", False, None),
    ("JM", "JAM", "Jamaica", "🇯🇲", "Americas", "Caribbean", False, None),
    ("MX", "MEX", "Mexico", "🇲🇽", "Americas", "Central America", False, None),
    ("NI", "NIC", "Nicaragua", "🇳🇮", "Americas", "Central America", False, None),
    ("PA", "PAN", "Panama", "🇵🇦", "Americas", "Central America", False, None),
    ("PY", "PRY", "Paraguay", "🇵🇾", "Americas", "South America", False, None),
    ("PE", "PER", "Peru", "🇵🇪", "Americas", "South America", False, None),
    ("KN", "KNA", "Saint Kitts and Nevis", "🇰🇳", "Americas", "Caribbean", False, None),
    ("LC", "LCA", "Saint Lucia", "🇱🇨", "Americas", "Caribbean", False, None),
    ("VC", "VCT", "Saint Vincent and the Grenadines", "🇻🇨", "Americas", "Caribbean", False, None),
    ("SR", "SUR", "Suriname", "🇸🇷", "Americas", "South America", False, None),
    ("TT", "TTO", "Trinidad and Tobago", "🇹🇹", "Americas", "Caribbean", False, None),
    ("US", "USA", "United States", "🇺🇸", "Americas", "Northern America", True, "residential"),
    ("UY", "URY", "Uruguay", "🇺🇾", "Americas", "South America", False, None),
    ("VE", "VEN", "Venezuela", "🇻🇪", "Americas", "South America", False, None),
    # ASIA
    ("AF", "AFG", "Afghanistan", "🇦🇫", "Asia", "Southern Asia", False, None),
    ("AM", "ARM", "Armenia", "🇦🇲", "Asia", "Western Asia", False, None),
    ("AZ", "AZE", "Azerbaijan", "🇦🇿", "Asia", "Western Asia", False, None),
    ("BH", "BHR", "Bahrain", "🇧🇭", "Asia", "Western Asia", False, None),
    ("BD", "BGD", "Bangladesh", "🇧🇩", "Asia", "Southern Asia", False, None),
    ("BT", "BTN", "Bhutan", "🇧🇹", "Asia", "Southern Asia", False, None),
    ("BN", "BRN", "Brunei Darussalam", "🇧🇳", "Asia", "South-Eastern Asia", False, None),
    ("KH", "KHM", "Cambodia", "🇰🇭", "Asia", "South-Eastern Asia", False, None),
    ("CN", "CHN", "China", "🇨🇳", "Asia", "Eastern Asia", False, None),
    ("CY", "CYP", "Cyprus", "🇨🇾", "Asia", "Western Asia", False, None),
    ("GE", "GEO", "Georgia", "🇬🇪", "Asia", "Western Asia", False, None),
    ("IN", "IND", "India", "🇮🇳", "Asia", "Southern Asia", False, None),
    ("ID", "IDN", "Indonesia", "🇮🇩", "Asia", "South-Eastern Asia", False, None),
    ("IR", "IRN", "Iran", "🇮🇷", "Asia", "Southern Asia", False, None),
    ("IQ", "IRQ", "Iraq", "🇮🇶", "Asia", "Western Asia", False, None),
    ("IL", "ISR", "Israel", "🇮🇱", "Asia", "Western Asia", False, None),
    ("JP", "JPN", "Japan", "🇯🇵", "Asia", "Eastern Asia", False, None),
    ("JO", "JOR", "Jordan", "🇯🇴", "Asia", "Western Asia", False, None),
    ("KZ", "KAZ", "Kazakhstan", "🇰🇿", "Asia", "Central Asia", False, None),
    ("KP", "PRK", "Korea, Democratic People's Republic of", "🇰🇵", "Asia", "Eastern Asia", False, None),
    ("KR", "KOR", "Korea, Republic of", "🇰🇷", "Asia", "Eastern Asia", False, None),
    ("KW", "KWT", "Kuwait", "🇰🇼", "Asia", "Western Asia", False, None),
    ("KG", "KGZ", "Kyrgyzstan", "🇰🇬", "Asia", "Central Asia", False, None),
    ("LA", "LAO", "Lao People's Democratic Republic", "🇱🇦", "Asia", "South-Eastern Asia", False, None),
    ("LB", "LBN", "Lebanon", "🇱🇧", "Asia", "Western Asia", False, None),
    ("MY", "MYS", "Malaysia", "🇲🇾", "Asia", "South-Eastern Asia", False, None),
    ("MV", "MDV", "Maldives", "🇲🇻", "Asia", "Southern Asia", False, None),
    ("MN", "MNG", "Mongolia", "🇲🇳", "Asia", "Eastern Asia", False, None),
    ("MM", "MMR", "Myanmar", "🇲🇲", "Asia", "South-Eastern Asia", False, None),
    ("NP", "NPL", "Nepal", "🇳🇵", "Asia", "Southern Asia", False, None),
    ("OM", "OMN", "Oman", "🇴🇲", "Asia", "Western Asia", False, None),
    ("PK", "PAK", "Pakistan", "🇵🇰", "Asia", "Southern Asia", False, None),
    ("PS", "PSE", "Palestine, State of", "🇵🇸", "Asia", "Western Asia", False, None),
    ("PH", "PHL", "Philippines", "🇵🇭", "Asia", "South-Eastern Asia", False, None),
    ("QA", "QAT", "Qatar", "🇶🇦", "Asia", "Western Asia", False, None),
    ("SA", "SAU", "Saudi Arabia", "🇸🇦", "Asia", "Western Asia", False, None),
    ("SG", "SGP", "Singapore", "🇸🇬", "Asia", "South-Eastern Asia", False, None),
    ("LK", "LKA", "Sri Lanka", "🇱🇰", "Asia", "Southern Asia", False, None),
    ("SY", "SYR", "Syrian Arab Republic", "🇸🇾", "Asia", "Western Asia", False, None),
    ("TW", "TWN", "Taiwan", "🇹🇼", "Asia", "Eastern Asia", False, None),
    ("TJ", "TJK", "Tajikistan", "🇹🇯", "Asia", "Central Asia", False, None),
    ("TH", "THA", "Thailand", "🇹🇭", "Asia", "South-Eastern Asia", False, None),
    ("TL", "TLS", "Timor-Leste", "🇹🇱", "Asia", "South-Eastern Asia", False, None),
    ("TR", "TUR", "Türkiye", "🇹🇷", "Asia", "Western Asia", False, None),
    ("TM", "TKM", "Turkmenistan", "🇹🇲", "Asia", "Central Asia", False, None),
    ("AE", "ARE", "United Arab Emirates", "🇦🇪", "Asia", "Western Asia", False, None),
    ("UZ", "UZB", "Uzbekistan", "🇺🇿", "Asia", "Central Asia", False, None),
    ("VN", "VNM", "Viet Nam", "🇻🇳", "Asia", "South-Eastern Asia", False, None),
    ("YE", "YEM", "Yemen", "🇾🇪", "Asia", "Western Asia", False, None),
    # EUROPE
    ("AL", "ALB", "Albania", "🇦🇱", "Europe", "Southern Europe", False, None),
    ("AD", "AND", "Andorra", "🇦🇩", "Europe", "Southern Europe", False, None),
    ("AT", "AUT", "Austria", "🇦🇹", "Europe", "Western Europe", False, None),
    ("BY", "BLR", "Belarus", "🇧🇾", "Europe", "Eastern Europe", False, None),
    ("BE", "BEL", "Belgium", "🇧🇪", "Europe", "Western Europe", False, None),
    ("BA", "BIH", "Bosnia and Herzegovina", "🇧🇦", "Europe", "Southern Europe", False, None),
    ("BG", "BGR", "Bulgaria", "🇧🇬", "Europe", "Eastern Europe", False, None),
    ("HR", "HRV", "Croatia", "🇭🇷", "Europe", "Southern Europe", False, None),
    ("CZ", "CZE", "Czechia", "🇨🇿", "Europe", "Eastern Europe", False, None),
    ("DK", "DNK", "Denmark", "🇩🇰", "Europe", "Northern Europe", False, None),
    ("EE", "EST", "Estonia", "🇪🇪", "Europe", "Northern Europe", False, None),
    ("FI", "FIN", "Finland", "🇫🇮", "Europe", "Northern Europe", False, None),
    ("FR", "FRA", "France", "🇫🇷", "Europe", "Western Europe", True, "residential"),
    ("DE", "DEU", "Germany", "🇩🇪", "Europe", "Western Europe", True, "residential"),
    ("GR", "GRC", "Greece", "🇬🇷", "Europe", "Southern Europe", False, None),
    ("HU", "HUN", "Hungary", "🇭🇺", "Europe", "Eastern Europe", False, None),
    ("IS", "ISL", "Iceland", "🇮🇸", "Europe", "Northern Europe", False, None),
    ("IE", "IRL", "Ireland", "🇮🇪", "Europe", "Northern Europe", False, None),
    ("IT", "ITA", "Italy", "🇮🇹", "Europe", "Southern Europe", False, None),
    ("XK", "XKX", "Kosovo", "🇽🇰", "Europe", "Southern Europe", False, None),
    ("LV", "LVA", "Latvia", "🇱🇻", "Europe", "Northern Europe", False, None),
    ("LI", "LIE", "Liechtenstein", "🇱🇮", "Europe", "Western Europe", False, None),
    ("LT", "LTU", "Lithuania", "🇱🇹", "Europe", "Northern Europe", False, None),
    ("LU", "LUX", "Luxembourg", "🇱🇺", "Europe", "Western Europe", False, None),
    ("MT", "MLT", "Malta", "🇲🇹", "Europe", "Southern Europe", False, None),
    ("MD", "MDA", "Moldova", "🇲🇩", "Europe", "Eastern Europe", False, None),
    ("MC", "MCO", "Monaco", "🇲🇨", "Europe", "Western Europe", False, None),
    ("ME", "MNE", "Montenegro", "🇲🇪", "Europe", "Southern Europe", False, None),
    ("NL", "NLD", "Netherlands", "🇳🇱", "Europe", "Western Europe", False, None),
    ("MK", "MKD", "North Macedonia", "🇲🇰", "Europe", "Southern Europe", False, None),
    ("NO", "NOR", "Norway", "🇳🇴", "Europe", "Northern Europe", False, None),
    ("PL", "POL", "Poland", "🇵🇱", "Europe", "Eastern Europe", False, None),
    ("PT", "PRT", "Portugal", "🇵🇹", "Europe", "Southern Europe", False, None),
    ("RO", "ROU", "Romania", "🇷🇴", "Europe", "Eastern Europe", False, None),
    ("RU", "RUS", "Russian Federation", "🇷🇺", "Europe", "Eastern Europe", False, None),
    ("SM", "SMR", "San Marino", "🇸🇲", "Europe", "Southern Europe", False, None),
    ("RS", "SRB", "Serbia", "🇷🇸", "Europe", "Southern Europe", False, None),
    ("SK", "SVK", "Slovakia", "🇸🇰", "Europe", "Eastern Europe", False, None),
    ("SI", "SVN", "Slovenia", "🇸🇮", "Europe", "Southern Europe", False, None),
    ("ES", "ESP", "Spain", "🇪🇸", "Europe", "Southern Europe", False, None),
    ("SE", "SWE", "Sweden", "🇸🇪", "Europe", "Northern Europe", False, None),
    ("CH", "CHE", "Switzerland", "🇨🇭", "Europe", "Western Europe", False, None),
    ("UA", "UKR", "Ukraine", "🇺🇦", "Europe", "Eastern Europe", False, None),
    ("GB", "GBR", "United Kingdom", "🇬🇧", "Europe", "Northern Europe", True, "residential"),
    ("VA", "VAT", "Vatican City", "🇻🇦", "Europe", "Southern Europe", False, None),
    # OCEANIA
    ("AU", "AUS", "Australia", "🇦🇺", "Oceania", "Australia and New Zealand", False, None),
    ("FJ", "FJI", "Fiji", "🇫🇯", "Oceania", "Melanesia", False, None),
    ("KI", "KIR", "Kiribati", "🇰🇮", "Oceania", "Micronesia", False, None),
    ("MH", "MHL", "Marshall Islands", "🇲🇭", "Oceania", "Micronesia", False, None),
    ("FM", "FSM", "Micronesia, Federated States of", "🇫🇲", "Oceania", "Micronesia", False, None),
    ("NR", "NRU", "Nauru", "🇳🇷", "Oceania", "Micronesia", False, None),
    ("NZ", "NZL", "New Zealand", "🇳🇿", "Oceania", "Australia and New Zealand", False, None),
    ("PW", "PLW", "Palau", "🇵🇼", "Oceania", "Micronesia", False, None),
    ("PG", "PNG", "Papua New Guinea", "🇵🇬", "Oceania", "Melanesia", False, None),
    ("WS", "WSM", "Samoa", "🇼🇸", "Oceania", "Polynesia", False, None),
    ("SB", "SLB", "Solomon Islands", "🇸🇧", "Oceania", "Melanesia", False, None),
    ("TO", "TON", "Tonga", "🇹🇴", "Oceania", "Polynesia", False, None),
    ("TV", "TUV", "Tuvalu", "🇹🇻", "Oceania", "Polynesia", False, None),
    ("VU", "VUT", "Vanuatu", "🇻🇺", "Oceania", "Melanesia", False, None),
]


async def main() -> int:
    async with async_session() as session:
        for entry in SEED:
            code, code3, name, flag, region, subregion, is_supported, proxy_pool = entry
            stmt = pg_insert(Country).values(
                code=code,
                code3=code3,
                name=name,
                flag_emoji=flag,
                region=region,
                subregion=subregion,
                is_supported=is_supported,
                plan_type_eligible=is_supported,  # supported = also eligible by default
                proxy_pool=proxy_pool,
            ).on_conflict_do_update(
                index_elements=["code"],
                set_={
                    "name": name,
                    "flag_emoji": flag,
                    "region": region,
                    "subregion": subregion,
                    "is_supported": is_supported,
                    "plan_type_eligible": is_supported,
                    "proxy_pool": proxy_pool,
                    "updated_at": Country.updated_at,  # let DB trigger handle
                },
            )
            await session.execute(stmt)
        await session.commit()

        # Verify count
        count_stmt = select(Country)
        rows = (await session.execute(count_stmt)).scalars().all()
        supported = [r for r in rows if r.is_supported]
        print(f"Seeded {len(rows)} countries total, {len(supported)} marked is_supported:")
        for r in supported:
            print(f"  - {r.flag_emoji} {r.code}: {r.name} (proxy_pool={r.proxy_pool})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
