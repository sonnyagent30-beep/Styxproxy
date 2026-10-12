"""Seed the blog posts table with real content.

P0-6 (Jul 22 2026): the original /backend/seed_blog_posts.sql had broken
apostrophe escaping (you'll, doesn't, we'll, etc.) that broke psql
parsing. This script inserts the same 7 posts via Python with correct
HTML escaping, and uses the freshly generated /blog/cover-N.png images
from the MiniMax M3 SVG → PNG pipeline.

Idempotent: uses slug as unique key — re-runs upsert.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras


# (slug, title, excerpt, content_html, cover_image, tags, published_at)
# Title/content lifted from the broken sql seed, apostrophes properly
# HTML-escaped (or just rewritten as 'X').
POSTS = [
    {
        "slug": "residential-vs-datacenter-proxies",
        "title": "Residential vs Datacenter Proxies: Which Should You Choose?",
        "excerpt": "Understand the fundamental differences between residential and datacenter proxies and which one fits your use case.",
        "content": """
<p>When it comes to choosing proxy services, the debate between residential and datacenter proxies is one of the most most important decisions you will make. Both have distinct advantages, and understanding them is critical for getting the most out of your proxy investment.</p>

<h2>What Are Residential Proxies?</h2>
<p>Residential proxies are IP addresses assigned by Internet Service Providers (ISPs) to real devices in actual households. When you use a residential proxy, websites see your requests as coming from a genuine home user, making them significantly harder to detect and block.</p>

<h2>What Are Datacenter Proxies?</h2>
<p>Datacenter proxies, on the other hand, are generated from cloud servers and data centers. They offer blazing-fast speeds and are significantly cheaper, but websites can more easily identify them as non-residential traffic.</p>

<h2>Key Differences</h2>
<ul>
<li><strong>Detection Rate:</strong> Residential proxies have a much lower detection rate.</li>
<li><strong>Speed:</strong> Datacenter proxies are typically 5-10x faster.</li>
<li><strong>Cost:</strong> Datacenter proxies are 60-80% cheaper.</li>
<li><strong>Geotargeting:</strong> Residential proxies offer more precise geographic targeting.</li>
</ul>

<h2>Which Should You Choose?</h2>
<p>For Nigerian web scraping and market research, residential proxies are highly recommended due to their ability to access local content without triggering anti-bot measures. For high-volume, speed-critical tasks like SEO monitoring or price aggregation, datacenter proxies offer the best value.</p>

<p>At <strong>Styxproxy</strong>, we offer both residential and datacenter proxies optimized for African markets, with ISP proxies covering major Nigerian cities including Lagos, Abuja, and Port Harcourt.</p>
""",
        "cover": "/blog/cover-1.png",
        "tags": ["proxies", "residential", "datacenter", "guide"],
        "published_at": "2026-06-01 09:00:00+00:00",
    },
    {
        "slug": "how-to-configure-socks5-proxies",
        "title": "How to Configure SOCKS5 Proxies in 5 Minutes",
        "excerpt": "A practical step-by-step guide to configuring your Styxproxy SOCKS5 credentials in any application.",
        "content": """
<p>Setting up SOCKS5 proxies does not have to be complicated. In this guide, we walk you through configuring your Styxproxy SOCKS5 credentials in five popular applications.</p>

<h2>What You Need</h2>
<ul>
<li>Your Styxproxy username and password</li>
<li>Your proxy IP address and port</li>
<li>The application you want to configure</li>
</ul>

<h2>Browser Configuration</h2>
<p>For Chrome or Edge, use an extension like Proxy SwitchyOmega. Add a new profile with:</p>
<ul>
<li><strong>Protocol:</strong> SOCKS5</li>
<li><strong>Server:</strong> [your proxy IP]</li>
<li><strong>Port:</strong> [your port]</li>
<li><strong>Username:</strong> [your username]</li>
<li><strong>Password:</strong> [your password]</li>
</ul>

<h2>Python (Requests Library)</h2>
<pre><code>proxies = {
    "http": "socks5://username:password@proxy_ip:port",
    "https": "socks5://username:password@proxy_ip:port"
}
response = requests.get(url, proxies=proxies)</code></pre>

<h2>curl</h2>
<pre><code>curl -x socks5h://username:password@proxy_ip:port https://example.com</code></pre>

<h2>Browser Automation (Playwright)</h2>
<pre><code>browser = await chromium.launch({
    proxy: {
        server: "socks5://proxy_ip:port",
        username: "your_username",
        password: "your_password"
    }
})</code></pre>

<p>Need help? Contact us at <a href="/contact">the contact form</a>.</p>
""",
        "cover": "/blog/cover-2.png",
        "tags": ["socks5", "setup", "guide", "configuration"],
        "published_at": "2026-06-08 10:00:00+00:00",
    },
    {
        "slug": "web-scraping-nigeria-guide",
        "title": "Web Scraping in Nigeria: A Practical Guide for 2026",
        "excerpt": "Everything you need to know about scraping Nigerian websites legally and effectively in 2026.",
        "content": """
<p>Nigeria is one of the fastest-growing digital markets in Africa, with millions of users on local e-commerce, classifieds, and news platforms. For developers and growth teams, the question is the same: how do you collect that public data reliably?</p>

<h2>Legal Considerations</h2>
<p>Public data on the open web is fair game in most jurisdictions if you respect robots.txt, do not bypass access controls, and do not scrape personal data at scale. When in doubt, consult local counsel.</p>

<h2>Locally-Sourced Proxies Make the Difference</h2>
<p>Datacenter IPs from abroad get blocked or rate-limited on local Nigerian sites — they are easy to fingerprint. Residential and 4G mobile proxies sourced from Nigerian ISPs look like genuine local users.</p>

<h2>What to Scrape</h2>
<ul>
<li>Jumia, Konga, and other e-commerce for price intelligence</li>
<li>Jobberman, MyJobMag, LinkedIn public listings for recruitment data</li>
<li>News sites for sentiment analysis on political/economic topics</li>
<li>Real estate platforms (PropertyPro, Cheki) for market research</li>
</ul>

<h2>Rate Limits &amp; Anti-Bot</h2>
<p>Most Nigerian sites do not run aggressive anti-bot stacks — a polite crawl with rotating residential IPs will work for months. If you need raw speed, hybrid datacenter+residential is the safest combination.</p>

<h2>Tooling</h2>
<p>Scrapy + rotating middleware for Python, Playwright for JavaScript-heavy sites, or vendor services like ScraperAPI. Pair any of these with Styxproxy local IPs and you are set.</p>
""",
        "cover": "/blog/cover-3.png",
        "tags": ["scraping", "nigeria", "market", "automation"],
        "published_at": "2026-06-15 10:00:00+00:00",
    },
    {
        "slug": "http-vs-socks5-vs-https-proxies",
        "title": "HTTP vs SOCKS5 vs HTTPS Proxies: Complete Comparison",
        "excerpt": "A clear breakdown of the three proxy protocols and when to use each.",
        "content": """
<p>If you have ever shopped for proxies and seen protocols like HTTP, HTTPS, and SOCKS5 listed side by side, you might have wondered whether they are mostly the same thing with different names. They are not.</p>

<h2>HTTP Proxy</h2>
<p>An HTTP proxy understands the HTTP protocol. It can read and modify request headers, cache responses, and apply rules like access control. It only works with HTTP traffic (HTTPS requires a CONNECT-method HTTP proxy).</p>

<h2>HTTPS Proxy</h2>
<p>An HTTPS proxy uses the CONNECT method to establish a TCP tunnel through the proxy. End-to-end TLS is preserved — the proxy never sees your plaintext. Best for privacy-sensitive workloads.</p>

<h2>SOCKS5 Proxy</h2>
<p>SOCKS5 is protocol-agnostic. It works at the TCP/UDP level and does not care whether traffic is HTTP, SMTP, BitTorrent, or anything else. It is the most flexible choice — and the slowest per-request because there is no protocol optimization.</p>

<h2>Which One Should You Use?</h2>
<ul>
<li><strong>Browser/web scraping</strong> → HTTP or HTTPS (whichever your tool supports)</li>
<li><strong>General TCP apps (email clients, games, custom tools)</strong> → SOCKS5</li>
<li><strong>Privacy-first</strong> → HTTPS or SOCKS5 over TLS</li>
</ul>

<p>Styxproxy supports all three out of the box — pick whichever your tool needs.</p>
""",
        "cover": "/blog/cover-4.png",
        "tags": ["protocols", "http", "socks5", "https", "comparison"],
        "published_at": "2026-06-22 10:00:00+00:00",
    },
    {
        "slug": "web-automation-stack-nigerian-businesses",
        "title": "Building an Affordable Web Automation Stack for Nigerian Businesses",
        "excerpt": "How small Nigerian businesses can automate leads, pricing, and ops on a tight budget.",
        "content": """
<p>If you run a small Nigerian e-commerce or services business, automation can save 10+ hours a week — but you do not need a developer team. Here is the minimum viable stack.</p>

<h2>The Three Buckets</h2>
<ul>
<li><strong>Lead capture:</strong> scrape competitor pricing on Jumia/Konga with rotating residential proxies, push to a Google Sheet</li>
<li><strong>Social media:</strong> 4G mobile proxies + a scheduler to post to Instagram and TikTok without bans</li>
<li><strong>Operations:</strong> monitor delivery partners, alert on price changes, auto-reply to common WhatsApp questions via Charon</li>
</ul>

<h2>Total Cost</h2>
<p>A working stack for a single operator costs about ₦50,000-100,000/month in proxy spend plus a free scheduler like Buffer or n8n. That is less than hiring a part-time VA — and runs 24/7.</p>

<h2>Setup Time</h2>
<p>Weekend. The biggest blocker is usually proxy sourcing, not the automation tooling. Styxproxy covers the proxy layer end to end.</p>

<h2>What Not to Automate</h2>
<p>Cold outreach at scale (gets numbers flagged), review manipulation (illegal), and anything that requires a Nigerian bank-grade OTP (out of scope for proxies alone).</p>
""",
        "cover": "/blog/cover-5.png",
        "tags": ["automation", "nigeria", "business", "stack"],
        "published_at": "2026-07-01 10:00:00+00:00",
    },
    {
        "slug": "proxy-authentication-methods",
        "title": "Proxy Authentication Methods Explained: IP Whitelist vs Username/Password",
        "excerpt": "IP whitelisting vs username/password — which proxy authentication method is right for your use case.",
        "content": """
<p>Every proxy service has to authenticate you somehow. There are two mainstream methods, and the choice affects how you operate.</p>

<h2>IP Whitelisting</h2>
<p>You give the proxy provider your public IP, they whitelist it, and any connection from that IP is automatically allowed. No credentials to manage. Drawback: if your IP changes (home ISP, mobile, VPN), you have to update the whitelist.</p>

<h2>Username + Password</h2>
<p>You embed credentials in your client (browser, script, app). Works from any IP. Drawback: credentials leak in code repos and logs if you are not careful.</p>

<h2>When to Use Which</h2>
<ul>
<li><strong>Stable office/home connection</strong> → IP whitelist (cleaner)</li>
<li><strong>Traveling / dynamic IP / multiple machines</strong> → Username + password</li>
<li><strong>Sharing across a team</strong> → Username + password with per-seat accounts</li>
</ul>

<h2>Styxproxy Default</h2>
<p>Both methods are supported. Default is username + password for flexibility. Add IP whitelist as a second factor for tighter security.</p>
""",
        "cover": "/blog/cover-6.png",
        "tags": ["auth", "ip-whitelist", "credentials", "security"],
        "published_at": "2026-07-08 10:00:00+00:00",
    },
    {
        "slug": "4g-mobile-proxies-social-media",
        "title": "4G Mobile Proxies: Why They Are King for Social Media Automation",
        "excerpt": "How 4G mobile proxies from Nigerian carriers provide unmatched stealth for social media automation.",
        "content": """
<p>If you have ever managed more than five Instagram accounts from the same IP, you have seen the shadowban. Platforms fingerprint datacenter IPs as soon as they touch the auth flow. Residential helps, but mobile is in a class of its own.</p>

<h2>What Makes Mobile Proxies Special</h2>
<p>Mobile carrier IPs (MTN, Airtel, Glo, 9mobile in Nigeria) are on CGNAT — thousands of subscribers share a single public IP. That means every request looks like it could be one of thousands of real users, and platforms cannot block the IP without also blocking real customers.</p>

<h2>Use Cases</h2>
<ul>
<li>Multi-account Instagram / TikTok management</li>
<li>Ad verification across geographies</li>
<li>Sneaker copping and limited-release monitoring</li>
<li>Local SERP scraping from a real mobile device perspective</li>
</ul>

<h2>Throughput vs Stealth Trade-off</h2>
<p>Mobile proxies are slower per-request than datacenter. They are also more expensive. The trade is intentional: you buy invisibility, not speed.</p>

<h2>How Styxproxy Sells Them</h2>
<p>Rotating pool of Nigerian carrier SIMs behind a clean NAT gateway. Per-GB or unlimited plans. No throttling on individual accounts.</p>
""",
        "cover": "/blog/cover-7.png",
        "tags": ["4g", "mobile", "social-media", "instagram"],
        "published_at": "2026-07-15 10:00:00+00:00",
    },
]

# Schema:
# id              uuid
# title           text
# slug            text unique
# content         text
# excerpt         text
# cover_image_url text
# author          text
# status          text     draft|pending|approved|published|retracted
# tags            text[]
# featured        bool     default false
# published_at    timestamptz
# created_at      timestamptz
# updated_at      timestamptz


def upsert_post(cursor, post: dict):
    """Insert or update a post by slug."""
    sql = """
    INSERT INTO posts (id, title, slug, content, excerpt, cover_image_url,
                       author, status, tags, view_count, published_at, featured,
                       created_at, updated_at)
    VALUES (gen_random_uuid(), %s, %s, %s, %s, %s,
            %s, 'published', %s, 0, %s, TRUE,
            %s, %s)
    ON CONFLICT (slug) DO UPDATE SET
        title = EXCLUDED.title,
        content = EXCLUDED.content,
        excerpt = EXCLUDED.excerpt,
        cover_image_url = EXCLUDED.cover_image_url,
        tags = EXCLUDED.tags,
        updated_at = EXCLUDED.updated_at
    RETURNING id
    """
    now = datetime.now(timezone.utc)
    cursor.execute(sql, (
        post["title"],
        post["slug"],
        post["content"].strip(),
        post["excerpt"],
        post["cover"],
        "Oyebiyi Ayomide",
        psycopg2.extras.Json(post["tags"]),
        post["published_at"],
        now,
        now,
    ))
    return cursor.fetchone()[0]


def main():
    """Connect, upsert posts, report."""
    conn = psycopg2.connect(
        host="127.0.0.1",
        database="styxproxy",
        user="styxproxy",
        password="styxproxy",
    )
    conn.autocommit = False
    cur = conn.cursor()
    inserted = 0
    for post in POSTS:
        pid = upsert_post(cur, post)
        inserted += 1
        print(f"  ok: {post['slug']:50s} -> {pid}")
    conn.commit()
    cur.execute("SELECT count(*) FROM posts")
    total = cur.fetchone()[0]
    print(f"\nupserted={inserted}  total_posts={total}")
    conn.close()


if __name__ == "__main__":
    main()
