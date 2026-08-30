"""
Start the AI Code Review backend server.

Usage:
  python run.py

Demo / production (no auto-reload):
  Set APP_ENV=demo in .env  OR  python run.py --demo
"""

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Start AI Code Review API")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode (no file reload, stabler for presentations)",
    )
    args = parser.parse_args()

    if args.demo:
        os.environ["APP_ENV"] = "demo"
        os.environ["APP_RELOAD"] = "false"

    # Import after env flags so Settings picks them up
    import uvicorn
    from app.core.config import settings

    if not settings.openai_api_key:
        print(
            "WARNING: OPENAI_API_KEY is empty in backend/.env — "
            "pattern scan will still work, but AI section analysis will be limited.",
            file=sys.stderr,
        )

    print(f"AI Code Review API starting on http://{settings.app_host}:{settings.app_port}")
    print(f"Environment: {settings.app_env} | reload={settings.should_reload}")
    print("Health check: http://127.0.0.1:8001/api/health")
    print("API docs:     http://127.0.0.1:8001/docs")

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.should_reload,
    )


if __name__ == "__main__":
    main()
