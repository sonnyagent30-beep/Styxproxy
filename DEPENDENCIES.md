# Styxproxy Dependency & Third-Party Service Registry

## Backend Python Dependencies

| Package | Version | Purpose | Critical? |
|---------|---------|---------|-----------|
| fastapi | 0.133.1 | Web framework | Yes |
| uvicorn[standard] | 0.41.0 | ASGI server | Yes |
| sqlalchemy[asyncio] | 2.0.51 | ORM | Yes |
| asyncpg | 0.31.0 | PostgreSQL async driver | Yes |
| pydantic[email] | 2.13.4 | Data validation | Yes |
| pydantic-settings | 2.14.2 | Config management | Yes |
| python-jose[cryptography] | 3.5.0 | JWT handling | Yes |
| passlib[bcrypt] | 1.7.4 | Password hashing | Yes |
| bcrypt | 4.3.0 | Password hashing | Yes |
| pyotp | 2.9.0 | TOTP 2FA | Yes |
| httpx | 0.28.1 | HTTP client | Yes |
| slowapi | 0.1.10 | Rate limiting | Yes |
| structlog | 26.1.0 | Structured logging | No |
| sentry-sdk | 2.64.0 | Error tracking | No |
| redis | 8.0.1 | Redis client | Yes |
| python-multipart | 0.0.27 | Form parsing | Yes |
| python-dotenv | 1.2.2 | Env loading | No |
| PyJWT | 2.10.1 | JWT (legacy) | No |

## Frontend npm Dependencies

| Package | Version | Purpose | Critical? |
|---------|---------|---------|-----------|
| next | 15.3.x | React framework | Yes |
| react | 19.1.0 | UI library | Yes |
| react-dom | 19.1.0 | DOM rendering | Yes |
| @sentry/nextjs | 10.68.0 | Error tracking | No |
| tailwindcss | 4 | CSS framework | Yes |
| framer-motion | 12.42.2 | Animations | No |
| zustand | 5.0.14 | State management | Yes |
| zod | 4.4.3 | Schema validation | Yes |
| react-globe.gl | 2.27.2 | 3D globe | No |
| three | 0.180.0 | 3D rendering | No |
| @react-three/fiber | 9.6.1 | React Three.js | No |
| qrcode | 1.5.4 | QR generation | No |
| playwright | 1.50.0 | E2E testing | No |

## Docker Images

| Image | Version | Purpose |
|-------|---------|---------|
| grafana/grafana | 11.6.0 | Monitoring dashboards |
| grafana/loki | 3.3.2 | Log aggregation |
| n8n | latest | Workflow automation |
| postgres | 16 | Database (migrating from Contabo) |
| redis | 7 | Cache (migrating from Contabo) |

## Third-Party Services

| Service | Purpose | Endpoint | Fallback |
|---------|---------|----------|----------|
| Flutterwave | Payment processing | api.flutterwave.com | Paystack |
| Resend | Email delivery | api.resend.com | — |
| Longcat2.0 | LLM (Charon AI) | api.longcat.ai | — |
| Vercel | Frontend hosting | styxproxy.com | — |
| Cloudflare | DNS + CDN | — | — |
| GitHub | Source control | github.com | — |
| Sentry | Error tracking | sentry.io | — |
| Upstream proxy providers | Proxy delivery | Various | Simulator mode |

## Update Schedule

| Component | Tool | Frequency |
|-----------|------|-----------|
| Python deps | Dependabot + pip-audit | Weekly |
| npm deps | Dependabot + npm audit | Weekly |
| Docker images | Manual review | Monthly |
| System packages | unattended-upgrades | Weekly (security) |
| SSL certificates | certbot | Auto-renew |
| Health checks | Custom script | Every 5 min |
| Dependency audit | Custom script | Weekly (Monday) |
| Backups | pg_dump + WAL | Daily + continuous |
