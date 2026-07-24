from .config import Settings
from .models import ChatRequest, RouteDecision

SIMPLE_TASKS = {"qa", "q&a", "extract", "extract_field", "keyword_search", "search"}
COMPLEX_TASKS = {"compare", "summarize_long", "summarize"}


def infer_task_type(request: ChatRequest) -> str:
    if request.routing.task_type:
        return request.routing.task_type
    text = " ".join(
        m.content if isinstance(m.content, str) else ""
        for m in request.messages
    ).lower()
    if "compare" in text or "so sánh" in text:
        return "compare"
    if "summarize" in text or "summary" in text or "tóm tắt" in text:
        return "summarize"
    if "extract" in text or "trích xuất" in text:
        return "extract"
    return "qa"


def is_complex(request: ChatRequest) -> bool:
    task = infer_task_type(request)
    if task in COMPLEX_TASKS:
        return True
    if request.routing.page_count > 10:
        return True
    if request.routing.document_count is not None and request.routing.document_count > 2:
        return True
    return False


def choose_route(request: ChatRequest, settings: Settings) -> RouteDecision:
    task_type = infer_task_type(request)

    if is_complex(request):
        return RouteDecision(
            model=settings.chat_model_complex,
            reason=f"complex_task:{task_type}",
            task_type=task_type,
        )

    confidence = request.routing.confidence_score
    if confidence is not None and confidence < settings.confidence_threshold:
        return RouteDecision(
            model=settings.chat_model_complex,
            reason=f"low_confidence:{confidence:.3f}",
            task_type=task_type,
        )

    return RouteDecision(
        model=settings.chat_model_simple,
        reason=f"simple_task:{task_type}",
        task_type=task_type,
    )


def route_metadata(decision: RouteDecision, request_id: str) -> dict:
    return {"request_id": request_id, **decision.model_dump()}
