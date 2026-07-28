import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
const environment = process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "production";

if (dsn) {
  Sentry.init({
    dsn,
    environment,
    tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE || 0.1),
    // IMPORTANT: replay is opted-in to avoid GDPR/privacy concerns. Enable
    // only after configuring the Session Replay privacy settings and adding
    // the user-facing opt-in banner.
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 0,
    debug: false,
  });
}
