"""
Automation Script 2: API Health Monitor
Polls /health and /health/db on a configurable interval.
Logs degraded/down states, prints a live dashboard, and sends
an email alert when the API goes down or recovers.

Usage:
    python scripts/health_monitor.py                         # poll every 30s
    python scripts/health_monitor.py --interval 60           # poll every 60s
    python scripts/health_monitor.py --url http://localhost:8000 --interval 15
    python scripts/health_monitor.py --alert-email ops@portflow.ai
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/health_monitor.log", mode="a"),
    ],
)
logger = logging.getLogger("health_monitor")

HEALTH_REPORT_PATH = Path("logs/health_status.json")

ENDPOINTS = [
    "/api/v1/health",
    "/api/v1/health/db",
]

STATUS_COLORS = {
    "healthy": "\033[92m",
    "degraded": "\033[93m",
    "unhealthy": "\033[91m",
    "timeout": "\033[91m",
    "error": "\033[91m",
}
RESET = "\033[0m"


async def _check_endpoint(client: httpx.AsyncClient, base_url: str, path: str, timeout: float) -> dict:
    url = base_url.rstrip("/") + path
    start = time.monotonic()
    try:
        response = await client.get(url, timeout=timeout)
        elapsed_ms = round((time.monotonic() - start) * 1000)
        body = {}
        try:
            body = response.json()
        except Exception:
            pass
        status = body.get("status", "unknown") if response.status_code == 200 else "unhealthy"
        return {
            "endpoint": path,
            "http_status": response.status_code,
            "status": status,
            "elapsed_ms": elapsed_ms,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except httpx.TimeoutException:
        return {
            "endpoint": path,
            "http_status": None,
            "status": "timeout",
            "elapsed_ms": round(timeout * 1000),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "endpoint": path,
            "http_status": None,
            "status": "error",
            "error": str(exc),
            "elapsed_ms": 0,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }


def _overall_status(results: list[dict]) -> str:
    statuses = {r["status"] for r in results}
    if "timeout" in statuses or "error" in statuses or "unhealthy" in statuses:
        return "unhealthy"
    if "degraded" in statuses:
        return "degraded"
    return "healthy"


def _print_dashboard(results: list[dict], overall: str, iteration: int) -> None:
    print(f"\n{'─'*55}")
    print(f"  PortFlow AI — Health Monitor  |  Check #{iteration}  |  {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'─'*55}")
    color = STATUS_COLORS.get(overall, "")
    print(f"  Overall: {color}{overall.upper()}{RESET}")
    print()
    for r in results:
        c = STATUS_COLORS.get(r["status"], "")
        err = f"  ({r.get('error', '')})" if r.get("error") else ""
        print(f"  {r['endpoint']:<25}  {c}{r['status']:<10}{RESET}  {r['elapsed_ms']}ms{err}")
    print(f"{'─'*55}")


def _save_status(results: list[dict], overall: str) -> None:
    HEALTH_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_REPORT_PATH.write_text(json.dumps({
        "overall": overall,
        "last_checked": datetime.now(timezone.utc).isoformat(),
        "endpoints": results,
    }, indent=2))


async def _send_alert(email: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        logger.warning("SMTP not configured — alert skipped: %s", subject)
        return
    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = email
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=settings.SMTP_TLS,
        )
        logger.info("Alert email sent to %s: %s", email, subject)
    except Exception as exc:
        logger.error("Failed to send alert email: %s", exc)


async def main(args: argparse.Namespace) -> None:
    logger.info("Health monitor started → %s  interval=%ds", args.url, args.interval)
    previous_overall = "healthy"
    iteration = 0

    async with httpx.AsyncClient() as client:
        while True:
            iteration += 1
            results = await asyncio.gather(*[
                _check_endpoint(client, args.url, path, timeout=args.timeout)
                for path in ENDPOINTS
            ])
            overall = _overall_status(list(results))

            _print_dashboard(list(results), overall, iteration)
            _save_status(list(results), overall)

            if overall != "healthy":
                logger.warning("Status: %s", overall)
            else:
                logger.info("Status: healthy")

            # Alert on transition: healthy → unhealthy or back
            if args.alert_email:
                if overall == "unhealthy" and previous_overall != "unhealthy":
                    await _send_alert(
                        args.alert_email,
                        "[PortFlow AI] ALERT: API is DOWN",
                        f"The PortFlow AI API at {args.url} is reporting status: {overall}\n\n"
                        + json.dumps(list(results), indent=2),
                    )
                elif overall == "healthy" and previous_overall == "unhealthy":
                    await _send_alert(
                        args.alert_email,
                        "[PortFlow AI] RECOVERED: API is back online",
                        f"The PortFlow AI API at {args.url} has recovered.\n\n"
                        + json.dumps(list(results), indent=2),
                    )

            previous_overall = overall

            if not args.watch:
                break
            await asyncio.sleep(args.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PortFlow AI — API Health Monitor")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--interval", type=int, default=30, help="Poll interval in seconds (default: 30)")
    parser.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds (default: 10)")
    parser.add_argument("--alert-email", metavar="EMAIL", help="Email address for down/recovery alerts")
    parser.add_argument("--watch", action="store_true", default=True, help="Keep polling (default: True)")
    parser.add_argument("--once", dest="watch", action="store_false", help="Check once then exit")
    asyncio.run(main(parser.parse_args()))
