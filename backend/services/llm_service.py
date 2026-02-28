"""
GPT-4o integration: extraction verification, financial analysis, vision OCR.
Uses structured prompts from prompts/*. Prompt builder, response parsing, retries, settings from settingsJson.
"""
import json
import os
from typing import Any, Optional

from openai import OpenAI
from prompts.extraction_prompt import EXTRACTION_PROMPT
from prompts.analysis_prompt import ANALYSIS_PROMPT
from prompts.vision_prompt import VISION_PROMPT

def _client():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY must be set for LLM calls")
    return OpenAI(api_key=key)


def _build_system_message(prompt_config: dict) -> str:
    """Assemble system message from aiRole + systemRole + objective."""
    role = prompt_config.get("aiRole", "")
    system = prompt_config.get("systemRole", "")
    objective = prompt_config.get("objective", "")
    parts = [role, system]
    if objective:
        parts.append(f"OBJECTIVE\n{objective}")
    return "\n\n".join(p for p in parts if p)


def _build_user_message(prompt_config: dict, data: dict | str) -> str:
    """User message from taskInstructions + taskInput + taskOutputFormat + taskExample + data."""
    instructions = prompt_config.get("taskInstructions", "")
    task_input = prompt_config.get("taskInput", "")
    output_format = prompt_config.get("taskOutputFormat", "")
    example = prompt_config.get("taskExample", "")

    sections = [instructions]

    if task_input:
        sections.append(f"INPUT SPECIFICATION\n{task_input}")

    if output_format:
        sections.append(f"OUTPUT FORMAT (respond in JSON)\n{output_format}")

    if example:
        sections.append(f"EXAMPLE\n{example}")

    data_str = json.dumps(data, default=str) if isinstance(data, dict) else data
    sections.append(f"INPUT DATA\n{data_str}")

    return "\n\n".join(s for s in sections if s)


def _call_chat(
    system: str,
    user: str,
    settings: Optional[dict] = None,
    image_url: Optional[str] = None,
) -> str:
    settings = settings or {}
    content = [{"type": "text", "text": user}]
    if image_url:
        content.insert(0, {"type": "image_url", "image_url": {"url": image_url}})

    api_kwargs = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
        "temperature": settings.get("temperature", 0),
        "max_tokens": settings.get("max_tokens", 1000),
    }
    if settings.get("topP") is not None:
        api_kwargs["top_p"] = settings["topP"]
    if settings.get("response_format") == "json_object":
        api_kwargs["response_format"] = {"type": "json_object"}

    for attempt in range(3):
        try:
            resp = _client().chat.completions.create(**api_kwargs)
            return resp.choices[0].message.content or "{}"
        except Exception as e:
            if attempt == 2:
                raise
            continue
    return "{}"


def verify_extraction(redacted_data: dict) -> dict:
    """Call 1: Extraction verification using extraction_prompt."""
    sys = _build_system_message(EXTRACTION_PROMPT)
    user = _build_user_message(EXTRACTION_PROMPT, redacted_data)
    raw = _call_chat(sys, user, EXTRACTION_PROMPT.get("settingsJson"))
    return json.loads(raw) if isinstance(raw, str) else raw


def analyze_financials(
    structured_fields: dict,
    rrsp_room: float,
    tfsa_room: float,
    province: str,
    tax_year: int,
    prior_net_income: Optional[float] = None,
    capital_loss_cf: Optional[float] = None,
    hbp_balance: Optional[float] = None,
    prior_year_data: Optional[dict] = None,
    current_year: Optional[int] = None,
) -> dict:
    """Call 2: Financial analysis using analysis_prompt."""
    cra_data = {
        "rrsp_room": rrsp_room,
        "tfsa_room": tfsa_room,
        "province": province,
        "tax_year": tax_year,
        "current_year": current_year or (tax_year + 1),
        "prior_net_income": prior_net_income,
        "capital_loss_cf": capital_loss_cf,
        "hbp_balance": hbp_balance,
    }
    data = {"structured_fields": structured_fields, **cra_data}
    if prior_year_data:
        data["prior_year_data"] = prior_year_data
    sys = _build_system_message(ANALYSIS_PROMPT)
    user = _build_user_message(ANALYSIS_PROMPT, data)
    raw = _call_chat(sys, user, ANALYSIS_PROMPT.get("settingsJson"))
    return json.loads(raw) if isinstance(raw, str) else raw


def extract_via_vision(image_base64: str, mime: str = "image/png") -> dict:
    """Vision OCR using vision_prompt; input is base64-encoded image."""
    url = f"data:{mime};base64,{image_base64}"
    sys = _build_system_message(VISION_PROMPT)
    user = _build_user_message(VISION_PROMPT, "[base64 image provided via image_url parameter]")
    raw = _call_chat(sys, user, VISION_PROMPT.get("settingsJson"), image_url=url)
    return json.loads(raw) if isinstance(raw, str) else raw
