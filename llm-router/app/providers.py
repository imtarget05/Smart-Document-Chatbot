import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

import httpx

from .config import Settings
from .models import ChatMessage, ChatRequest, RouteDecision
from .routing import route_metadata


class ProviderError(RuntimeError):
    pass


def _max_tokens(request: ChatRequest) -> int:
    return int(request.options.get("num_predict", request.options.get("max_tokens", 2048)))


def _temperature(request: ChatRequest) -> float:
    return float(request.options.get("temperature", 0.3))


def _ollama_response(content: str, decision: RouteDecision, request_id: str) -> dict[str, Any]:
    return {
        "model": decision.model,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
        "router": route_metadata(decision, request_id),
    }


def _message_dict(message: ChatMessage) -> dict[str, Any]:
    payload = message.model_dump(exclude_none=True)
    if not payload.get("images"):
        payload.pop("images", None)
    return payload


def _normalize_openai_part(item: dict[str, Any]) -> dict[str, Any]:
    part_type = item.get("type")
    if part_type not in {"image", "input_image"}:
        return item

    url = item.get("image_url") or item.get("url")
    if isinstance(url, dict):
        url = url.get("url")
    source = item.get("source")
    if not url and isinstance(source, dict) and source.get("data"):
        media_type = source.get("media_type", "image/jpeg")
        url = f"data:{media_type};base64,{source['data']}"
    if not url:
        return item
    return {"type": "image_url", "image_url": {"url": url}}


def _attachment_image_url(attachment: str | dict[str, Any]) -> str | None:
    if isinstance(attachment, str):
        return None
    url = attachment.get("url") or attachment.get("image_url")
    if isinstance(url, dict):
        url = url.get("url")
    if url:
        return str(url)
    data = attachment.get("data") or attachment.get("base64")
    if not data:
        return None
    media_type = attachment.get("content_type") or attachment.get("mime_type") or "image/jpeg"
    return f"data:{media_type};base64,{data}"


def _openai_messages(
    messages: list[ChatMessage], attachments: list[str | dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for message in messages:
        content: Any = message.content
        if message.images:
            parts: list[dict[str, Any]] = []
            if isinstance(content, str) and content:
                parts.append({"type": "text", "text": content})
            elif isinstance(content, list):
                parts.extend(_normalize_openai_part(item) for item in content)
            for image in message.images:
                url = image if image.startswith(("http://", "https://", "data:")) else f"data:image/jpeg;base64,{image}"
                parts.append({"type": "image_url", "image_url": {"url": url}})
            content = parts
        elif isinstance(content, list):
            content = [_normalize_openai_part(item) for item in content]
        result.append({"role": message.role, "content": content})

    attachment_parts = [
        {"type": "image_url", "image_url": {"url": url}}
        for attachment in attachments or []
        if (url := _attachment_image_url(attachment))
    ]
    if attachment_parts:
        target = next((message for message in reversed(result) if message["role"] == "user"), None)
        if target is not None:
            content = target["content"]
            if isinstance(content, str):
                content = ([{"type": "text", "text": content}] if content else [])
            target["content"] = [*content, *attachment_parts]
    return result


def _anthropic_messages(messages: list[ChatMessage]) -> tuple[str | None, list[dict[str, Any]]]:
    systems: list[str] = []
    result: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "system":
            systems.append(str(message.content))
        else:
            role = "assistant" if message.role == "assistant" else "user"
            result.append({"role": role, "content": message.content})
    return ("\n\n".join(systems) or None), result


class ProviderClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def chat(self, request: ChatRequest, decision: RouteDecision, request_id: str) -> dict[str, Any]:
        if decision.provider == "local":
            return await self._local_chat(request, decision, request_id)
        if decision.provider == "anthropic":
            return await self._anthropic_chat(request, decision, request_id)
        if decision.provider == "nvidia":
            return await self._nvidia_chat(request, decision, request_id)
        return await self._openai_chat(request, decision, request_id)

    async def stream_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        if decision.provider == "local":
            async for chunk in self._local_stream(request, decision, request_id):
                yield chunk
        elif decision.provider == "anthropic":
            async for chunk in self._anthropic_stream(request, decision, request_id):
                yield chunk
        elif decision.provider == "nvidia":
            async for chunk in self._nvidia_stream(request, decision, request_id):
                yield chunk
        else:
            async for chunk in self._openai_stream(request, decision, request_id):
                yield chunk


    async def embeddings(self, body: dict[str, Any]) -> dict[str, Any]:
        response = await self.client.post(
            f"{self.settings.local_base_url.rstrip('/')}/api/embeddings",
            json=body,
            timeout=self.settings.cloud_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    async def _local_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        body = request.model_dump(exclude={"routing"}, exclude_none=True)
        body.update({"model": self.settings.local_model, "stream": False})
        try:
            async with asyncio.timeout(self.settings.local_timeout_seconds):
                response = await self.client.post(
                    f"{self.settings.local_base_url.rstrip('/')}/api/chat", json=body,
                    timeout=self.settings.local_timeout_seconds
                )
                response.raise_for_status()
                payload = response.json()
        except TimeoutError as exc:
            raise ProviderError("local_timeout") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"local_error:{type(exc).__name__}") from exc
        payload["router"] = route_metadata(decision, request_id)
        return payload

    async def _anthropic_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        self._require_key(self.settings.anthropic_api_key, "ANTHROPIC_API_KEY")
        system, messages = _anthropic_messages(request.messages)
        body: dict[str, Any] = {
            "model": decision.model,
            "messages": messages,
            "max_tokens": _max_tokens(request),
            "temperature": _temperature(request),
        }
        if system:
            body["system"] = system
        try:
            response = await self.client.post(
                self.settings.anthropic_api_url,
                json=body,
                headers={
                    "x-api-key": self.settings.anthropic_api_key,
                    "anthropic-version": self.settings.anthropic_version,
                },
                timeout=self.settings.cloud_timeout_seconds,
            )
            self._raise_provider_status(response, "anthropic")
            payload = response.json()
            content = "".join(block.get("text", "") for block in payload.get("content", []))
        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderError(f"anthropic_error:{type(exc).__name__}") from exc
        return _ollama_response(content, decision, request_id)

    async def _openai_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        self._require_key(self.settings.openai_api_key, "OPENAI_API_KEY")
        try:
            response = await self.client.post(
                self.settings.openai_api_url,
                json={
                    "model": decision.model,
                    "messages": _openai_messages(request.messages, request.routing.attachments),
                    "max_tokens": _max_tokens(request),
                    "temperature": _temperature(request),
                },
                headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                timeout=self.settings.cloud_timeout_seconds,
            )
            self._raise_provider_status(response, "openai")
            content = response.json()["choices"][0]["message"]["content"] or ""
        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"openai_error:{type(exc).__name__}") from exc
        return _ollama_response(content, decision, request_id)

    async def _local_stream(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        body = request.model_dump(exclude={"routing"}, exclude_none=True)
        body.update({"model": self.settings.local_model, "stream": True})
        try:
            async with self.client.stream(
                "POST", f"{self.settings.local_base_url.rstrip('/')}/api/chat", json=body,
                timeout=self.settings.local_timeout_seconds
            ) as response:
                response.raise_for_status()
                lines = response.aiter_lines()
                try:
                    first = await asyncio.wait_for(anext(lines), self.settings.local_timeout_seconds)
                except (TimeoutError, StopAsyncIteration) as exc:
                    raise ProviderError("local_timeout") from exc
                if first:
                    yield self._decorate_ollama_line(first, decision, request_id)
                async for line in lines:
                    if line:
                        yield self._decorate_ollama_line(line, decision, request_id)
        except ProviderError:
            raise
        except httpx.HTTPError as exc:
            raise ProviderError(f"local_error:{type(exc).__name__}") from exc

    async def _anthropic_stream(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        self._require_key(self.settings.anthropic_api_key, "ANTHROPIC_API_KEY")
        system, messages = _anthropic_messages(request.messages)
        body: dict[str, Any] = {
            "model": decision.model,
            "messages": messages,
            "max_tokens": _max_tokens(request),
            "temperature": _temperature(request),
            "stream": True,
        }
        if system:
            body["system"] = system
        headers = {
            "x-api-key": self.settings.anthropic_api_key,
            "anthropic-version": self.settings.anthropic_version,
        }
        try:
            async with self.client.stream(
                "POST", self.settings.anthropic_api_url, json=body, headers=headers,
                timeout=self.settings.cloud_timeout_seconds,
            ) as response:
                self._raise_provider_status(response, "anthropic")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    delta = event.get("delta", {})
                    if event.get("type") == "content_block_delta" and delta.get("type") == "text_delta":
                        yield self._ollama_chunk(delta.get("text", ""), False, decision, request_id)
        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderError(f"anthropic_error:{type(exc).__name__}") from exc
        yield self._ollama_chunk("", True, decision, request_id)

    async def _openai_stream(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        self._require_key(self.settings.openai_api_key, "OPENAI_API_KEY")
        body = {
            "model": decision.model,
            "messages": _openai_messages(request.messages, request.routing.attachments),
            "max_tokens": _max_tokens(request),
            "temperature": _temperature(request),
            "stream": True,
        }
        try:
            async with self.client.stream(
                "POST", self.settings.openai_api_url, json=body,
                headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                timeout=self.settings.cloud_timeout_seconds,
            ) as response:
                self._raise_provider_status(response, "openai")
                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    event = json.loads(line[6:])
                    content = event.get("choices", [{}])[0].get("delta", {}).get("content") or ""
                    if content:
                        yield self._ollama_chunk(content, False, decision, request_id)
        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError, IndexError, TypeError) as exc:
            raise ProviderError(f"openai_error:{type(exc).__name__}") from exc
        yield self._ollama_chunk("", True, decision, request_id)

    @staticmethod
    def _require_key(value: str, name: str) -> None:
        if not value:
            raise ProviderError(f"missing_configuration:{name}")

    @staticmethod
    def _raise_provider_status(response: httpx.Response, provider: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(f"{provider}_http_{response.status_code}") from exc

    @staticmethod
    def _decorate_ollama_line(
        line: str, decision: RouteDecision, request_id: str
    ) -> bytes:
        payload = json.loads(line)
        payload["router"] = route_metadata(decision, request_id)
        return (json.dumps(payload, ensure_ascii=False) + "\n").encode()

    @staticmethod
    def _ollama_chunk(
        content: str, done: bool, decision: RouteDecision, request_id: str
    ) -> bytes:
        payload = _ollama_response(content, decision, request_id)
        payload["done"] = done
        if not done:
            payload.pop("done_reason", None)
        return (json.dumps(payload, ensure_ascii=False) + "\n").encode()

    async def _nvidia_chat(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> dict[str, Any]:
        self._require_key(self.settings.nvidia_api_key, "NVIDIA_API_KEY")
        self._require_key(self.settings.nvidia_model, "NVIDIA_MODEL_ID")

        url = f"{self.settings.nvidia_api_url.rstrip('/')}/{decision.model}"
        headers = {
            "Authorization": f"Bearer {self.settings.nvidia_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        messages = _openai_messages(request.messages, request.routing.attachments)
        body = {
            "messages": messages,
            "temperature": _temperature(request),
            "max_tokens": _max_tokens(request),
        }

        try:
            response = await self.client.post(
                url,
                json=body,
                headers=headers,
                timeout=self.settings.cloud_timeout_seconds,
            )

            # Handle 202 Accepted (asynchronous processing on NVIDIA NVCF)
            if response.status_code == 202:
                req_id = response.headers.get("NVCF-REQID")
                if not req_id:
                    try:
                        req_id = response.json().get("reqId")
                    except Exception:
                        pass
                
                if not req_id:
                    raise ProviderError("nvidia_missing_req_id")

                status_url = f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/{req_id}"
                max_polls = 60
                poll_count = 0
                while poll_count < max_polls:
                    await asyncio.sleep(1.0)
                    poll_count += 1
                    poll_resp = await self.client.get(
                        status_url,
                        headers={"Authorization": f"Bearer {self.settings.nvidia_api_key}"},
                        timeout=self.settings.cloud_timeout_seconds,
                    )
                    if poll_resp.status_code == 200:
                        response = poll_resp
                        break
                    elif poll_resp.status_code == 202:
                        continue
                    else:
                        raise ProviderError(f"nvidia_poll_status_{poll_resp.status_code}")
                else:
                    raise ProviderError("nvidia_poll_timeout")

            self._raise_provider_status(response, "nvidia")
            resp_data = response.json()

            content = ""
            if "choices" in resp_data and len(resp_data["choices"]) > 0:
                content = resp_data["choices"][0].get("message", {}).get("content") or ""
            elif "content" in resp_data:
                content = resp_data["content"]
            else:
                content = json.dumps(resp_data)

        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"nvidia_error:{type(exc).__name__}") from exc

        return _ollama_response(content, decision, request_id)

    async def _nvidia_stream(
        self, request: ChatRequest, decision: RouteDecision, request_id: str
    ) -> AsyncIterator[bytes]:
        res = await self._nvidia_chat(request, decision, request_id)
        content = res["message"]["content"]
        yield self._ollama_chunk(content, False, decision, request_id)
        yield self._ollama_chunk("", True, decision, request_id)

