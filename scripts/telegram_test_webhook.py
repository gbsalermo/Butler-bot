"""Configura um bot Telegram separado para testar o Worker local do Butler.

Usa apenas a stdlib. Procura TELEGRAM_BOT_TOKEN e TELEGRAM_WEBHOOK_SECRET no
ambiente e, se ausentes, tenta carregar cloudflare/.dev.vars.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEV_VARS = ROOT / "cloudflare" / ".dev.vars"


def _load_dev_vars() -> None:
    if not DEV_VARS.exists():
        return
    for raw_line in DEV_VARS.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _token() -> str:
    _load_dev_vars()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token.startswith("COLE_AQUI"):
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN ausente. Copie cloudflare/.dev.vars.example "
            "para cloudflare/.dev.vars e use o token do bot de teste."
        )
    return token


def _call(method: str, payload: dict[str, str] | None = None) -> dict:
    token = _token()
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urlencode(payload or {}).encode("utf-8")
    request = Request(url, data=data, method="POST")
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def set_webhook(public_url: str) -> dict:
    endpoint = public_url.rstrip("/") + "/telegram/webhook"
    payload = {"url": endpoint, "drop_pending_updates": "true"}
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if secret:
        payload["secret_token"] = secret
    result = _call("setWebhook", payload)
    result["local_endpoint"] = endpoint
    return result


def info() -> dict:
    return _call("getWebhookInfo")


def delete() -> dict:
    return _call("deleteWebhook", {"drop_pending_updates": "true"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerencia o webhook do bot de teste do Butler.")
    sub = parser.add_subparsers(dest="command", required=True)

    set_parser = sub.add_parser("set", help="Aponta o bot para o tunnel do Worker local.")
    set_parser.add_argument("public_url", help="URL pública do tunnel, ex.: https://abc.trycloudflare.com")
    sub.add_parser("info", help="Mostra o webhook atual do bot de teste.")
    sub.add_parser("delete", help="Remove o webhook do bot de teste.")

    args = parser.parse_args()
    if args.command == "set":
        result = set_webhook(args.public_url)
    elif args.command == "info":
        result = info()
    else:
        result = delete()

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
