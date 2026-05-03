"""Prompt templates for the MedSim Triage agent.

All user-facing prompts are Turkish. The system prompts strictly bind the
model to the agent's narrow tasks: (a) symptom extraction, (b) follow-up
question generation, (c) plain-language explanation of an already-decided
triage outcome. The model NEVER decides the triage color itself.
"""

from __future__ import annotations

SYSTEM_GUARDRAIL_TR = (
    "Sen bir TIBBİ TRİYAJ EĞİTİM ve SİMÜLASYON asistanısın. "
    "Tıbbi tanı koymazsın, tedavi ve ilaç önermezsin, doz bilgisi vermezsin. "
    "Triyaj renk kararını SEN VERMEZSİN; karar dışarıdaki kural motoruna aittir. "
    "Görevin yalnızca: (1) hastanın anlattığını yapılandırılmış semptom verisine "
    "dönüştürmek, (2) eksik bilgi varsa tek bir kısa soru üretmek, "
    "(3) sana verilmiş bir kararı sade Türkçe ile açıklamak. "
    "Acil durum şüphesinde kullanıcıyı 112'yi aramaya yönlendir."
)


SYMPTOM_EXTRACTION_SYSTEM_TR = (
    SYSTEM_GUARDRAIL_TR
    + "\n\n"
    + "Şu an görevin: Kullanıcının mesajından yapılandırılmış semptom verisi "
    "çıkarmak. Yalnızca verilen JSON şemasına uygun çıktı üret. Bilinmeyen "
    "alanları null bırak veya boş liste yap. Tahmin etme."
)


QUESTION_GENERATION_SYSTEM_TR = (
    SYSTEM_GUARDRAIL_TR
    + "\n\n"
    + "Şu an görevin: Eksik bilgilerden EN KRİTİK olanı belirleyip kullanıcıya "
    "tek, kısa, sade bir Türkçe soru sor. Birden fazla soru sorma. "
    "Tıbbi terim yerine günlük dil kullan. Soruyu doğrudan yaz, ön açıklama yapma."
)


EXPLANATION_SYSTEM_TR = (
    SYSTEM_GUARDRAIL_TR
    + "\n\n"
    + "Şu an görevin: Sana verilen TRİYAJ KARARINI ve tetiklenen kuralı "
    "kullanıcıya 3-5 cümlelik sade Türkçe ile açıklamak. Yeni bir karar verme, "
    "kararı değiştirme. KIRMIZI ise kullanıcıyı net biçimde 112'yi aramaya yönlendir. "
    "Doz, ilaç adı veya kesin tanı verme."
)


def build_extraction_messages(
    user_text: str,
    prior_context: str | None = None,
) -> list[dict[str, str]]:
    """Compose chat messages for the symptom-extraction LLM call."""
    user_block = (
        f"Önceki bağlam:\n{prior_context}\n\n" if prior_context else ""
    ) + f"Kullanıcı mesajı:\n{user_text}"
    return [
        {"role": "system", "content": SYMPTOM_EXTRACTION_SYSTEM_TR},
        {"role": "user", "content": user_block},
    ]


def build_question_messages(
    extracted_summary: str,
    missing_fields: list[str],
) -> list[dict[str, str]]:
    """Compose chat messages for the follow-up-question LLM call."""
    fields_block = ", ".join(missing_fields) if missing_fields else "(belirtilmemiş)"
    user_block = (
        f"Şu ana kadar çıkarılan bilgi:\n{extracted_summary}\n\n"
        f"Eksik alanlar: {fields_block}\n\n"
        "Lütfen yalnızca tek bir kısa Türkçe soru üret."
    )
    return [
        {"role": "system", "content": QUESTION_GENERATION_SYSTEM_TR},
        {"role": "user", "content": user_block},
    ]


def build_explanation_messages(
    decision_summary: str,
    rule_summary: str | None,
) -> list[dict[str, str]]:
    """Compose chat messages for the decision-explanation LLM call."""
    rule_block = rule_summary or "(eşleşen spesifik kural yok; kırmızı bayrak/güvenlik kararı)"
    user_block = (
        f"TRİYAJ KARARI:\n{decision_summary}\n\n"
        f"TETİKLENEN KURAL:\n{rule_block}\n\n"
        "Lütfen kullanıcıya bu kararı 3-5 cümlede açıkla."
    )
    return [
        {"role": "system", "content": EXPLANATION_SYSTEM_TR},
        {"role": "user", "content": user_block},
    ]
