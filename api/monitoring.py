"""Optional error tracking (Sentry)."""

import os


def init_error_tracking(app):
    dsn = (os.environ.get("SENTRY_DSN") or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            environment=os.environ.get("FLASK_ENV", "development"),
        )
        app.logger.info("Sentry error tracking enabled")
    except Exception as exc:
        app.logger.warning("Sentry init failed: %s", exc)
