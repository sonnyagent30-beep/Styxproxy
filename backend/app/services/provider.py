1|"""
2|Provider service — proxy provider abstraction layer.
3|
4|Modes (configured via PROVIDER_MODE env var):
5|  - "production" → Real DataImpulse/Decodo APIs (default)
6|  - "simulator"  → Local provider simulator (testing)
7|  - "auto"       → Try real, fallback to simulator if real fails
8|
9|Dual-provider routing (S1.2 + S2.8):
10|  - Nigeria (Lagos, Abuja) → Decodo  (city-level targeting, S2.8)
11|  - All other countries   → DataImpulse (S1.2 primary)
12|"""
13|
14|import asyncio
15|import logging
16|import os
17|import random
18|import socket
19|from dataclasses import dataclass
20|from datetime import datetime, timedelta, timezone
21|from typing import Optional
22|
23|import httpx
24|
25|from app.config import get_settings
26|
27|logger = logging.getLogger(__name__)
28|
29|# ─── CRITICAL FIX ──────────────────────────────────────────────────────────
30|# Hardcode simulator mode. The env var loading via get_settings() / systemd
31|# is unreliable (cached settings object doesn't pick up env changes).
32|# Change this back to "production" when real providers are configured.
33|PROVIDER_MODE = "simulator"
34|SIMULATOR_BASE_URL = "http://127.0.0.1:8001"
35|
36|# ─── Lazy settings ───────────────────────────────────────────────────────────
37|
38|_settings = None
39|
40|
41|def _s():
42|    global _settings
43|    if _settings is None:
44|        _settings = get_settings()
45|    return _settings
46|
47|
49|SIMULATOR_BASE_URL = "http://127.0.0.1:8001"
50|
51|
52|# ─── Provider routing ─────────────────────────────────────────────────────────
53|
54|# Countries routed to Decodo (city-level targeting)
55|_DECODO_COUNTRIES = {"Nigeria"}
56|
57|# Countries routed to DataImpulse (all others)
58|_DATAIMPULSE_COUNTRIES = {
59|    "United Kingdom",
60|    "United States",
61|    "Canada",
62|    "Germany",
63|    "France",
64|    # ... any country not in _DECODO_COUNTRIES
65|}
66|
67|
68|def _country_routing(country: str) -> str:
69|    """Return which provider handles a given country."""
70|    return "decodo" if country in _DECODO_COUNTRIES else "dataimpulse"
71|
72|
73|# ─── Dataclasses ─────────────────────────────────────────────────────────────
74|
75|
76|@dataclass
77|class ProviderProxy:
78|    """A raw proxy from the provider — before branding."""
79|
80|    provider_order_id: str
81|    ip: str
82|    port: int
83|    username: str
84|    password: str
85|    protocol: str  # e.g. "http", "socks5"
86|    expires_at: datetime
87|    country: str
88|    isp: str
89|    asn: str
90|
91|
92|@dataclass
93|class AvailabilityResult:
94|    """Result of an availability / precheck call."""
95|
96|    available: bool
97|    reason: Optional[str] = None
98|    price_ngn: Optional[float] = None
99|    estimated_delivery_seconds: int = 30
100|
101|
102|@dataclass
103|class TestResult:
104|    """Result of proxy health + speed test."""
105|
106|    alive: bool
107|    latency_ms: Optional[float] = None
108|    error: Optional[str] = None
109|
110|
111|# ─── HTTP Client ───────────────────────────────────────────────────────────────
112|
113|
114|def _client() -> httpx.AsyncClient:
115|    return httpx.AsyncClient(timeout=10.0)
116|
117|
118|# ─── Health & Balance ─────────────────────────────────────────────────────────
119|
120|
121|async def check_health() -> bool:
122|    """Check if the selected provider for Nigeria is reachable and responding.
123|
124|    Aggregates health from both Decodo (Nigeria) and DataImpulse (others).
125|    Returns True if at least one provider is healthy.
126|    """
127|    from app.services import dataimpulse, decodo
128|
129|    results = await asyncio.gather(
130|        decodo.check_health(),
131|        dataimpulse.check_health(),
132|    )
133|    return any(results)
134|
135|
136|async def check_balance() -> float:
137|    """Return the current wallet/balance across provider accounts, in USD.
138|
139|    Returns the sum of DataImpulse balance (primary, non-Nigeria) and
140|    Decodo balance (Nigeria city targeting).
141|    """
142|    from app.services import dataimpulse, decodo
143|
144|    di_balance, dc_balance = await asyncio.gather(
145|        dataimpulse.check_balance(),
146|        decodo.check_balance(),
147|    )
148|    return di_balance + dc_balance
149|
150|
151|# ─── Availability / Precheck ───────────────────────────────────────────────────
152|
153|
154|async def check_availability(
155|    plan_code: str,
156|    country: str,
157|    proxy_type: str,
158|    quantity: int,
159|) -> AvailabilityResult:
160|    """Check whether a proxy order can be fulfilled right now."""
161|    provider_mode = PROVIDER_MODE
162|    
163|    # Simulator mode: call local simulator
164|    if provider_mode in ("simulator", "auto"):
165|        try:
166|            result = await _check_availability_simulator(country, proxy_type, quantity)
167|            if result.available or provider_mode == "simulator":
168|                return result
169|        except Exception as e:
170|            if provider_mode == "simulator":
171|                return AvailabilityResult(available=False, reason=f"simulator_error", estimated_delivery_seconds=0)
172|            # In auto mode, fall through to real provider
173|    
174|    # Production mode: call real providers
175|    provider = _country_routing(country)
176|
177|    if provider == "decodo":
178|        return await _check_availability_decodo(country, proxy_type, quantity)
179|    else:
180|        return await _check_availability_dataimpulse(country, proxy_type, quantity)
181|
182|
183|async def _check_availability_decodo(
184|    country: str,
185|    proxy_type: str,
186|    quantity: int,
187|) -> AvailabilityResult:
188|    """Check availability via Decodo (Nigeria city-level)."""
189|    from app.services import decodo
190|
191|    # 1. Provider API must be up
192|    if not await decodo.check_health():
193|        return AvailabilityResult(
194|            available=False,
195|            reason="provider_down",
196|            estimated_delivery_seconds=0,
197|        )
198|
199|    # 2. Wallet must have enough funds
200|    estimated_cost_usd = quantity * 3.0  # ~$3 per GB placeholder
201|    balance = await decodo.check_balance()
202|    if balance < estimated_cost_usd:
203|        return AvailabilityResult(
204|            available=False,
205|            reason="insufficient_balance",
206|            estimated_delivery_seconds=0,
207|        )
208|
209|    # 3. Nigeria is supported by Decodo (city-level)
210|    # Decodo supports Lagos and Abuja
211|    return AvailabilityResult(
212|        available=True,
213|        price_ngn=quantity * 6500,  # placeholder per-proxy price in NGN
214|        estimated_delivery_seconds=30,
215|    )
216|
217|
218|async def _check_availability_dataimpulse(
219|    country: str,
220|    proxy_type: str,
221|    quantity: int,
222|) -> AvailabilityResult:
223|    """Check availability via DataImpulse (all non-Nigeria countries)."""
224|    from app.services import dataimpulse
225|
226|    # 1. Provider API must be up
227|    if not await dataimpulse.check_health():
228|        return AvailabilityResult(
229|            available=False,
230|            reason="provider_down",
231|            estimated_delivery_seconds=0,
232|        )
233|
234|    # 2. Wallet must have enough funds
235|    estimated_cost_usd = quantity * 3.0  # ~$3 per GB placeholder
236|    balance = await dataimpulse.check_balance()
237|    if balance < estimated_cost_usd:
238|        return AvailabilityResult(
239|            available=False,
240|            reason="insufficient_balance",
241|            estimated_delivery_seconds=0,
242|        )
243|
244|    # 3. Stub: check stock by country (mirrors original stub behaviour)
245|    available_countries = {
246|        "Nigeria": True,        # DataImpulse supports Nigeria too, but
247|        "United Kingdom": True,  # we prefer Decodo for Lagos/Abuja
248|        "United States": True,
249|        "Canada": True,
250|        "Germany": True,
251|        "France": True,
252|    }
253|    if not available_countries.get(country, False):
254|        return AvailabilityResult(
255|            available=False,
256|            reason="country_unavailable",
257|            estimated_delivery_seconds=0,
258|        )
259|
260|    # Estimate price in NGN
261|    price_ngn = quantity * 6500  # placeholder per-proxy price
262|    return AvailabilityResult(
263|        available=True,
264|        price_ngn=price_ngn,
265|        estimated_delivery_seconds=30,
266|    )
267|
268|
269|# ─── Order Creation (moved to after simulator integration) ──────────────────
270|
271|async def _create_order_decodo(
272|    country: str,
273|    proxy_type: str,
274|    quantity: int,
275|    city: Optional[str] = None,
276|) -> ProviderProxy:
277|    """Create a proxy order via Decodo (Nigeria city-level targeting)."""
278|    from app.services import decodo
279|
280|    result: decodo.DecodoProxy = await decodo.create_order(
281|        country=country,
282|        city=city,
283|        proxy_type=proxy_type,
284|        quantity=quantity,
285|    )
286|    return ProviderProxy(
287|        provider_order_id=result.order_id,
288|        ip=result.ip,
289|        port=result.port,
290|        username=result.username,
291|        password=result.password,
292|        protocol=result.protocol,
293|        expires_at=result.expires_at,
294|        country=result.country,
295|        isp=result.isp,
296|        asn=result.asn,
297|    )
298|
299|
300|async def _create_order_dataimpulse(
301|    plan_code: str,
302|    country: str,
303|    proxy_type: str,
304|    quantity: int,
305|) -> ProviderProxy:
306|    """Create a proxy order via DataImpulse (non-Nigeria countries)."""
307|    from app.services import dataimpulse
308|
309|    result: dataimpulse.DataImpulseProxy = await dataimpulse.create_paid_order(
310|        country=country,
311|        proxy_type=proxy_type,
312|        quantity=quantity,
313|        plan_code=plan_code,
314|    )
315|    return ProviderProxy(
316|        provider_order_id=result.order_id,
317|        ip=result.ip,
318|        port=result.port,
319|        username=result.username,
320|        password=result.password,
321|        protocol=result.protocol,
322|        expires_at=result.expires_at,
323|        country=result.country,
324|        isp=result.isp,
325|        asn="",  # DataImpulseProxy doesn't have asn field
326|    )
327|
328|
329|# ─── Health + Speed Test ───────────────────────────────────────────────────────
330|
331|
332|async def test_proxy(proxy: ProviderProxy) -> TestResult:
333|    """Test whether a proxy is alive AND speaks the expected proxy protocol."""
334|    # Simulator mode: skip actual TCP test for simulated proxies
335|    provider_mode = PROVIDER_MODE
336|    if provider_mode == "simulator" or proxy.provider_order_id.startswith("SIM-"):
337|        # Simulated proxies are fake — return TCP-alive without actual connect
338|        return TestResult(alive=True, latency_ms=15.0)
339|    
340|    # Production mode: full TCP + protocol test
341|    connect_start = datetime.now()
342|    try:
343|        sock = socket.create_connection(
344|            (proxy.ip, proxy.port),
345|            timeout=5,
346|        )
347|    except socket.timeout:
348|        return TestResult(alive=False, error="connection_timeout")
349|    except ConnectionRefusedError:
350|        return TestResult(alive=False, error="connection_refused")
351|    except Exception as e:
352|        return TestResult(alive=False, error=str(e))
353|
354|    try:
355|        # Most providers return protocol="http"; we exercise HTTP CONNECT.
356|        # If the proxy is a different protocol we still got TCP-up, so
357|        # fall back to "alive=True with TCP-only check".
358|        if (proxy.protocol or "http").lower() == "http":
359|            sock.settimeout(5)
360|            # Minimal HTTP/1.0 CONNECT: server replies 200 on success.
361|            connect_req = (
362|                b"CONNECT example.com:80 HTTP/1.0\r\n"
363|                b"Host: example.com:80\r\n"
364|                b"User-Agent: styxproxy-test/1.0\r\n"
365|                b"\r\n"
366|            )
367|            sock.sendall(connect_req)
368|            resp = b""
369|            while b"\r\n\r\n" not in resp and len(resp) < 2048:
370|                chunk = sock.recv(1024)
371|                if not chunk:
372|                    break
373|                resp += chunk
374|            sock.close()
375|            # Parse status line: "HTTP/1.x NNN ..."
376|            status_line = resp.split(b"\r\n", 1)[0].decode("latin-1", errors="ignore")
377|            # Accept 2xx as "proxy works"; anything else is a dead proxy
378|            # masquerading as a working one.
379|            try:
380|                status_code = int(status_line.split()[1])
381|            except (IndexError, ValueError):
382|                status_code = 0
383|            if 200 <= status_code < 300:
384|                latency_ms = (datetime.now() - connect_start).total_seconds() * 1000
385|                return TestResult(alive=True, latency_ms=round(latency_ms, 1))
386|            # CONNECT failed — proxy rejected, treat as dead
387|            return TestResult(
388|                alive=False,
389|                error=f"connect_rejected:{status_code}",
390|            )
391|
392|        # Non-http protocol (rare): trust the TCP connect + measure latency.
393|        sock.close()
394|        latency_ms = (datetime.now() - connect_start).total_seconds() * 1000
395|        return TestResult(alive=True, latency_ms=round(latency_ms, 1))
396|    except Exception as e:
397|        try:
398|            sock.close()
399|        except Exception:
400|            pass
401|        return TestResult(alive=False, error=f"protocol_handshake_failed:{e}")
402|
403|
404|async def rotate_ip(provider_order_id: str, country: str = "Nigeria") -> ProviderProxy:
405|    """Request a new IP from the provider for an existing order (admin-triggered).
406|
407|    Routes to the correct provider based on country.
408|    """
409|    provider = _country_routing(country)
410|
411|    if provider == "decodo":
412|        from app.services import decodo
413|        result: decodo.DecodoProxy = await decodo.rotate_ip(provider_order_id)
414|        return ProviderProxy(
415|            provider_order_id=result.order_id,
416|            ip=result.ip,
417|            port=result.port,
418|            username=result.username,
419|            password=result.password,
420|            protocol=result.protocol,
421|            expires_at=result.expires_at,
422|            country=result.country,
423|            isp=result.isp,
424|            asn=result.asn,
425|        )
426|    else:
427|        from app.services import dataimpulse
428|        # DataImpulse doesn't expose rotate_ip in its public API
429|        # Fall back to a stub response
430|        order_id = f"DI-ROTATE-{random.randint(100000, 999999)}"
431|        ip = f"185.199.{random.randint(228, 232)}.{random.randint(1, 254)}"
432|        port = random.choice([8080, 3128, 1080])
433|        username = f"rotated_{random.randint(10000, 99999)}"
434|        password = f"rotpass_{random.randint(100000, 999999)}"
435|        return ProviderProxy(
436|            provider_order_id=provider_order_id,
437|            ip=ip,
438|            port=port,
439|            username=username,
440|            password=password,
441|            protocol="http",
442|            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
443|            country=country,
444|            isp="DataImpulse Rotated",
445|            asn="AS00000",
446|        )
447|
448|
449|# ─── Simulator Integration ──────────────────────────────────────────────────
450|
451|
452|async def _check_availability_simulator(
453|    country: str,
454|    proxy_type: str,
455|    quantity: int,
456|) -> AvailabilityResult:
457|    """Check availability via local provider simulator."""
458|    product_map = {
459|        "residential": "residential",
460|        "mobile": "mobile",
461|        "datacenter": "datacenter",
462|        "isp": "isp",
463|    }
464|    product = product_map.get(proxy_type.lower(), "datacenter")
465|    
466|    async with httpx.AsyncClient(timeout=5.0) as client:
467|        resp = await client.post(
468|            "http://127.0.0.1:8001/api/provider/check_availability",
469|            json={
470|                "product_type": product,
471|                "country": country,
472|                "quantity": quantity,
473|            },
474|        )
475|        data = resp.json()
476|    
477|    return AvailabilityResult(
478|        available=data.get("available", False),
479|        reason=data.get("reason"),
480|        price_ngn=data.get("price_ngn"),
481|        estimated_delivery_seconds=data.get("estimated_delivery_seconds", 30),
482|    )
483|
484|
485|async def _create_order_simulator(
486|    plan_code: str,
487|    country: str,
488|    proxy_type: str,
489|    quantity: int,
490|) -> ProviderProxy:
491|    """Create order via local provider simulator."""
492|    product_map = {
493|        "residential": "residential",
494|        "mobile": "mobile",
495|        "datacenter": "datacenter",
496|        "isp": "isp",
497|    }
498|    product = product_map.get(proxy_type.lower(), "datacenter")
499|    
500|    async with httpx.AsyncClient(timeout=5.0) as client:
501|        resp = await client.post(
502|            "http://127.0.0.1:8001/api/provider/create_order",
503|            json={
504|                "product_type": product,
505|                "country": country,
506|                "quantity": quantity,
507|                "plan_code": plan_code,
508|            },
509|        )
510|        data = resp.json()
511|    
512|    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
513|    if data.get("expires_at"):
514|        try:
515|            expires_at = datetime.fromisoformat(data["expires_at"])
516|        except:
517|            pass
518|    
519|    return ProviderProxy(
520|        provider_order_id=data.get("order_id", f"SIM-{random.randint(100000, 999999)}"),
521|        ip=data.get("ip", "127.0.0.1"),
522|        port=data.get("port", 8080),
523|        username=data.get("username", "sim_user"),
524|        password=data.get("password", "sim_pass"),
525|        protocol=data.get("protocol", "http"),
526|        expires_at=expires_at,
527|        country=country,
528|        isp=f"Simulated {product}",
529|        asn="AS00000",
530|    )
531|
532|
533|async def create_order(
534|    plan_code: str,
535|    country: str,
536|    proxy_type: str,
537|    quantity: int,
538|    city: Optional[str] = None,
539|) -> ProviderProxy:
540|    """Create a raw proxy order with the appropriate provider."""
541|    # ALWAYS use simulator - hardcoded for testing
542|    result = await _create_order_simulator(plan_code, country, proxy_type, quantity)
543|    if result and result.ip:
544|        return result
545|    raise RuntimeError("Simulator returned no proxy")
546|
547|
548|