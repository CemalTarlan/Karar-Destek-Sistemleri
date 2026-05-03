#!/usr/bin/env python
"""Check that LM Studio's local server is reachable.

Usage:
    python scripts/lm_studio_check.py

Exit codes:
    0 — server reachable, model list printed
    1 — server unreachable; instructions printed
"""

from __future__ import annotations

import sys

import httpx

from medsim.config import get_settings


def _print_setup_instructions(base_url: str) -> None:
    print("=" * 60)
    print("LM Studio sunucusuna ULAŞILAMADI.")
    print(f"Hedef: {base_url}/models")
    print("=" * 60)
    print()
    print("Lütfen şu adımları sırayla uygulayın:")
    print("  1. LM Studio uygulamasını açın.")
    print("  2. Sol panelden 'Developer' (Geliştirici) sekmesine geçin.")
    print("  3. 'Start Server' düğmesine basın (varsayılan port: 1234).")
    print("  4. Bir modelin yüklü ve seçili olduğundan emin olun.")
    print("  5. Bu komutu yeniden çalıştırın:")
    print("       python scripts/lm_studio_check.py")
    print()
    print("Farklı bir adres/port kullanıyorsanız .env dosyasında")
    print("LM_STUDIO_BASE_URL değerini güncelleyin.")


def main() -> int:
    settings = get_settings()
    base_url = settings.lm_studio_base_url.rstrip("/")

    print(f"LM Studio kontrol ediliyor: {base_url}/models ...")
    try:
        response = httpx.get(f"{base_url}/models", timeout=5.0)
    except httpx.HTTPError as exc:
        print(f"Bağlantı hatası: {exc}")
        print()
        _print_setup_instructions(base_url)
        return 1

    if response.status_code != 200:
        print(f"Sunucu beklenmeyen durum kodu döndürdü: HTTP {response.status_code}")
        print(f"Yanıt: {response.text[:200]}")
        _print_setup_instructions(base_url)
        return 1

    try:
        payload = response.json()
    except ValueError:
        print("Sunucu yanıtı geçerli JSON değil.")
        _print_setup_instructions(base_url)
        return 1

    models = payload.get("data", []) if isinstance(payload, dict) else []
    print()
    print("LM Studio sunucusu ÇALIŞIYOR.")
    print(f"Yüklü model sayısı: {len(models)}")
    if not models:
        print("UYARI: Henüz yüklü model yok. LM Studio'dan bir model indirip yükleyin.")
    else:
        print("Erişilebilir modeller:")
        for entry in models:
            model_id = entry.get("id") if isinstance(entry, dict) else str(entry)
            print(f"  • {model_id}")

    print()
    print("Hazır. .env dosyanızda LM_STUDIO_MODEL değerinin yukarıdaki")
    print("modellerden birinin id'si olduğundan emin olun.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
