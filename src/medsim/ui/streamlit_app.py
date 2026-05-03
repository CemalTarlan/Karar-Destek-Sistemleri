"""Streamlit chat UI for MedSim Triage.

Talks to the FastAPI backend over HTTP — no direct imports from `medsim`
internals (other than the API base-URL via env). Run with:

    streamlit run src/medsim/ui/streamlit_app.py
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st

API_BASE = os.environ.get("MEDSIM_API_BASE", "http://localhost:8000")
TIMEOUT = 60.0

COLOR_HEX = {"KIRMIZI": "#d32f2f", "SARI": "#f57c00", "YESIL": "#388e3c"}
COLOR_LABEL = {"KIRMIZI": "🟥 KIRMIZI", "SARI": "🟨 SARI", "YESIL": "🟩 YEŞİL"}

DISCLAIMER_TR = (
    "Bu sistem yalnızca EĞİTİM ve SİMÜLASYON amaçlıdır. Gerçek bir tıbbi "
    "değerlendirme, tanı veya tedavi önerisi sağlamaz. Acil bir durumda "
    "lütfen 112'yi arayın."
)


def _render_disclaimer_banner() -> None:
    st.markdown(
        f"""
        <div style="background-color:#b71c1c;color:white;padding:12px 16px;
                    border-radius:6px;font-weight:600;margin-bottom:12px;">
            ⚠️ {DISCLAIMER_TR}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _start_conversation() -> dict[str, Any] | None:
    try:
        r = httpx.post(f"{API_BASE}/triage/start", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as exc:
        st.error(f"API'ye ulaşılamadı: {exc}")
        return None


def _send_turn(conversation_id: str, message: str) -> dict[str, Any] | None:
    try:
        r = httpx.post(
            f"{API_BASE}/triage/turn",
            json={"conversation_id": conversation_id, "message": message},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        st.error(f"Sunucu hatası: {detail}")
        return None
    except httpx.HTTPError as exc:
        st.error(f"Bağlantı hatası: {exc}")
        return None


def _render_decision_panel(state: dict[str, Any]) -> None:
    decision = state.get("decision")
    if not decision:
        return
    color = decision.get("color", "YESIL")
    color_hex = COLOR_HEX.get(color, "#616161")
    label = COLOR_LABEL.get(color, color)

    st.markdown(
        f"""
        <div style="background-color:{color_hex};color:white;padding:18px;
                    border-radius:10px;font-size:28px;font-weight:700;
                    text-align:center;margin:12px 0;">
            {label}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if color == "KIRMIZI":
        st.markdown(
            """
            <a href="tel:112" style="display:block;background:#d32f2f;color:white;
               padding:14px;text-align:center;font-size:22px;font-weight:700;
               border-radius:8px;text-decoration:none;margin-bottom:12px;">
              📞 112'yi ARA
            </a>
            """,
            unsafe_allow_html=True,
        )

    rule_id = decision.get("triggered_rule_id")
    if rule_id:
        st.markdown(f"**Tetiklenen kural:** `{rule_id}`")

    st.markdown(f"**Gerekçe:** {decision.get('rationale', '')}")
    st.markdown(f"**Öneri:** {decision.get('recommendation', '')}")
    st.caption(f"Güven: {decision.get('confidence', 0):.0%}  •  ESI: {decision.get('esi_level')}")

    cols = st.columns(2)
    with cols[0]:
        if st.button("👍 Yardımcı oldu", key="fb_yes", use_container_width=True):
            st.toast("Geri bildiriminiz için teşekkürler.")
    with cols[1]:
        if st.button("👎 Yardımcı olmadı", key="fb_no", use_container_width=True):
            st.toast("Geri bildiriminiz için teşekkürler.")


def _render_sidebar(state: dict[str, Any]) -> None:
    with st.sidebar:
        st.header("Durum")
        st.write(f"**Adım:** {state.get('step', '?')}")
        st.write(f"**Tur sayısı:** {state.get('turn_count', 0)}")

        symptoms = state.get("extracted_symptoms")
        st.subheader("Tespit edilen semptomlar")
        if symptoms:
            for key, value in symptoms.items():
                if value not in (None, "", []):
                    st.write(f"- **{key}**: {value}")
        else:
            st.caption("Henüz semptom çıkarılmadı.")

        decision = state.get("decision") or {}
        red_flags = decision.get("red_flags", []) if isinstance(decision, dict) else []
        st.subheader("Kırmızı bayraklar")
        if red_flags:
            for rf in red_flags:
                st.error(rf)
        else:
            st.caption("Tetiklenen kırmızı bayrak yok.")


def main() -> None:
    st.set_page_config(page_title="MedSim Triage", page_icon="🚑", layout="centered")
    _render_disclaimer_banner()
    st.title("🚑 MedSim Triage — Eğitim Simülasyonu")

    if "conversation_id" not in st.session_state:
        start = _start_conversation()
        if start:
            st.session_state.conversation_id = start["conversation_id"]
            st.session_state.state = start["state"]
            st.session_state.history = [
                {"role": "assistant", "content": start.get("message", "")}
            ]
        else:
            st.stop()

    _render_sidebar(st.session_state.state)

    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    decision = (st.session_state.state or {}).get("decision")
    if decision:
        _render_decision_panel(st.session_state.state)
        st.info("Yeni bir konuşma başlatmak için sayfayı yenileyin.")
        return

    user_input = st.chat_input("Şikayetinizi yazın...")
    if not user_input:
        return

    st.session_state.history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    payload = _send_turn(st.session_state.conversation_id, user_input)
    if payload is None:
        return

    response = payload["response"]
    assistant_text = response["assistant_message"]
    st.session_state.state = response["state"]
    st.session_state.history.append({"role": "assistant", "content": assistant_text})

    with st.chat_message("assistant"):
        st.markdown(assistant_text)

    if response.get("is_decided"):
        _render_decision_panel(st.session_state.state)


if __name__ == "__main__":
    main()
