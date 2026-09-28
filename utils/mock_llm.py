"""Mock LLM — CHO SẴN, KHÔNG CẦN SỬA.

Trả lời tất định (cùng câu hỏi → cùng câu trả lời) nên không cần API key,
không tốn tiền, và test luôn cho kết quả ổn định.

Dùng:
    from utils.mock_llm import ask_llm
    result = ask_llm("Docker là gì?", history=[...])
    result["answer"], result["tokens_in"], result["tokens_out"], result["cost_usd"]
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import httpx

# Giá giả lập, tính theo 1.000 token (giống thang giá gpt-4o-mini)
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.00060

_TEMPLATES = [
    "Theo mình hiểu, {q} liên quan tới cách hệ thống được đóng gói và vận hành. "
    "Điểm mấu chốt là tách cấu hình ra khỏi code và giữ service ở trạng thái stateless.",
    "Câu hỏi hay. {q} thường được giải quyết bằng cách chuẩn hóa môi trường chạy: "
    "cùng một image chạy giống nhau ở laptop và trên cloud.",
    "Ngắn gọn: {q} phụ thuộc vào ba yếu tố — cấu hình qua biến môi trường, "
    "health check để orchestrator biết trạng thái, và giới hạn tài nguyên.",
    "Với {q}, cách làm phổ biến trong production là đặt một lớp gateway phía trước "
    "để lo authentication, rate limiting và bảo vệ chi phí.",
]


def _estimate_tokens(text: str) -> int:
    """Ước lượng thô: ~4 ký tự / token, tối thiểu 1."""
    return max(1, len(text) // 4)


def _get_env_val(key: str, default: str = "") -> str:
    """Đọc biến môi trường, ưu tiên os.getenv, fallback đọc từ file .env nếu có."""
    val = os.getenv(key)
    if val:
        return val.strip()
    for env_path in [Path(".env"), Path(__file__).resolve().parent.parent / ".env"]:
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == key:
                            return v.strip().strip("'\"")
            except Exception:
                pass
    return default


def _call_gemini_api(question: str, history: list[dict] | None = None) -> dict | None:
    """Gọi Google Gemini API nếu có GEMINI_API_KEY trong env."""
    api_key = _get_env_val("GEMINI_API_KEY")
    model = _get_env_val("LLM_MODEL", "gemini-3.5-flash-lite")
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    contents = []
    if history:
        for turn in history:
            role = "model" if turn.get("role") == "assistant" else "user"
            content = turn.get("content", "")
            if content:
                contents.append({"role": role, "parts": [{"text": str(content)}]})
    contents.append({"role": "user", "parts": [{"text": str(question)}]})

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                url,
                json={"contents": contents},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    answer = "".join(p.get("text", "") for p in parts)
                    usage = data.get("usageMetadata", {})
                    tokens_in = usage.get("promptTokenCount") or _estimate_tokens(question)
                    tokens_out = usage.get("candidatesTokenCount") or _estimate_tokens(answer)
                    cost = (
                        tokens_in / 1000 * PRICE_INPUT_PER_1K
                        + tokens_out / 1000 * PRICE_OUTPUT_PER_1K
                    )
                    return {
                        "answer": answer,
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "cost_usd": round(cost, 8),
                    }
    except Exception:
        pass
    return None


def ask_llm(question: str, history: list[dict] | None = None) -> dict:
    """Một lượt gọi LLM (thử gọi Gemini trước, nếu lỗi/thiếu key thì fallback về mock).

    Args:
        question: câu hỏi của người dùng.
        history: lịch sử hội thoại, list các dict {"role": ..., "content": ...}.

    Returns:
        dict gồm answer, tokens_in, tokens_out, cost_usd.
    """
    history = history or []

    # 1. Thử gọi API Gemini thật
    gemini_result = _call_gemini_api(question, history)
    if gemini_result is not None:
        return gemini_result

    # 2. Fallback về Mock LLM tất định (cho test / khi offline)
    digest = hashlib.sha256(question.strip().lower().encode("utf-8")).hexdigest()
    template = _TEMPLATES[int(digest[:8], 16) % len(_TEMPLATES)]
    answer = template.format(q=question.strip().rstrip("?") or "vấn đề bạn hỏi")

    if history:
        answer += f" (Mình đang nhớ {len(history)} lượt trao đổi trước đó.)"

    prompt_text = question + "".join(turn.get("content", "") for turn in history)
    tokens_in = _estimate_tokens(prompt_text)
    tokens_out = _estimate_tokens(answer)
    cost = (
        tokens_in / 1000 * PRICE_INPUT_PER_1K
        + tokens_out / 1000 * PRICE_OUTPUT_PER_1K
    )

    return {
        "answer": answer,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost, 8),
    }
