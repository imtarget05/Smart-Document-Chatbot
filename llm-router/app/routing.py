import re
from pathlib import PurePath
from typing import Any

from .config import Settings
from .models import ChatRequest, RouteDecision


COMPLEX_TASKS = {"compare", "summarize_long"}
LOCAL_TASKS = {"qa", "q&a", "extract", "extract_field", "keyword_search", "search"}
IMAGE_SUFFIXES = {".bmp", ".gif", ".heic", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


def _content_text(content: str | list[dict[str, Any]]) -> str:
    if isinstance(content, str):
        return content
    return " ".join(str(item.get("text", "")) for item in content if isinstance(item, dict))


def _has_image_part(content: str | list[dict[str, Any]]) -> bool:
    if not isinstance(content, list):
        return False
    return any(
        isinstance(item, dict) and item.get("type") in {"image", "image_url", "input_image"}
        for item in content
    )


def has_visual_input(request: ChatRequest) -> bool:
    context = request.routing
    if context.has_image:
        return True
    for attachment in context.attachments:
        if isinstance(attachment, str):
            values = [attachment]
        else:
            values = [
                str(attachment.get(key, ""))
                for key in ("content_type", "mime_type", "filename", "file_name", "name", "type")
            ]
            if attachment.get("is_scan") is True:
                return True
        for raw_value in values:
            value = raw_value.lower()
            if value.startswith("image/") or "scan" in value or PurePath(value).suffix in IMAGE_SUFFIXES:
                return True
    return any(message.images or _has_image_part(message.content) for message in request.messages)


def infer_task_type(request: ChatRequest) -> str:
    explicit = (request.routing.task_type or "").strip().lower()
    if explicit:
        return explicit

    text = " ".join(_content_text(message.content) for message in request.messages).lower()
    if re.search(r"\b(compare|comparison|contrast|diff|versus|vs\.?|so s\u00e1nh)\b", text):
        return "compare"
    if "executive summary" in text and "suggested questions" in text:
        return "summarize"
    if re.search(r"\b(summarize|summary|t\u00f3m t\u1eaft)\b", text):
        if request.routing.page_count > 10 or "long" in text or "detailed" in text:
            return "summarize_long"
        return "summarize"
    if re.search(r"\b(extract|field|tr\u00edch xu\u1ea5t)\b", text):
        return "extract_field"
    if re.search(r"\b(keyword|key word|t\u1eeb kh\u00f3a)\b", text):
        return "keyword_search"
    return "qa"


def infer_document_count(request: ChatRequest) -> int:
    if request.routing.document_count:
        return request.routing.document_count
    text = "\n".join(_content_text(message.content) for message in request.messages)
    labels = set()
    ignored = {"answer", "context", "conversation history", "question"}
    for label in re.findall(r"\[([^\]\n]{1,255})\]", text):
        normalized = label.strip().lower()
        if normalized and not normalized.isdigit() and normalized not in ignored:
            labels.add(normalized)
    return len(labels)


def choose_route(request: ChatRequest, settings: Settings) -> RouteDecision:
    task_type = infer_task_type(request)
    
    # Check if NVIDIA is configured for summarization
    if settings.nvidia_api_key and task_type in {"summarize", "summarize_long"}:
        return RouteDecision(
            provider="nvidia",
            model=settings.nvidia_model,
            reason=f"nvidia_summarization:{task_type}",
            task_type=task_type,
        )

    document_count = infer_document_count(request)
    if (
        has_visual_input(request)
        or document_count > 2
        or request.routing.page_count > 10
        or task_type in COMPLEX_TASKS
    ):
        if has_visual_input(request):
            reason = "visual_input"
        elif task_type in COMPLEX_TASKS:
            reason = f"complex_task:{task_type}"
        elif document_count > 2:
            reason = "document_count_gt_2"
        else:
            reason = "page_count_gt_10"
        return RouteDecision(
            provider="openrouter",
            model=settings.openrouter_model,
            reason=reason,
            task_type=task_type,
        )

    confidence = request.routing.confidence_score
    if confidence is not None and confidence < settings.confidence_threshold:
        return RouteDecision(
            provider="openrouter",
            model=settings.openrouter_model,
            reason=f"low_confidence:{confidence:.3f}",
            task_type=task_type,
            escalated=True,
        )

    return RouteDecision(
        provider="local",
        model=settings.local_model,
        reason=f"cost_optimized:{task_type if task_type in LOCAL_TASKS else 'default'}",
        task_type=task_type,
    )



def route_metadata(decision: RouteDecision, request_id: str) -> dict[str, Any]:
    return {"request_id": request_id, **decision.model_dump()}
