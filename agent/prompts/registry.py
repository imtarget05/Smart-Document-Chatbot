"""Prompt registry for centralized prompt management.

Supports YAML and JSON prompt files with variable substitution,
version selection, and in-memory caching.
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"


class PromptError(Exception):
    """Base exception for prompt registry errors."""


class PromptNotFoundError(PromptError):
    """Raised when a prompt name is not found."""


class PromptRenderError(PromptError):
    """Raised when template variable substitution fails."""


class PromptRegistry:
    """Thread-safe prompt registry with file loading and caching."""

    def __init__(self, prompts_dir: Optional[Path] = None):
        self._prompts_dir = prompts_dir or _PROMPTS_DIR
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._loaded = False

    def _load_all(self) -> None:
        """Load all prompt files from the prompts directory into cache."""
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            self._cache.clear()
            if not self._prompts_dir.exists():
                logger.warning("Prompts directory not found: %s", self._prompts_dir)
                self._loaded = True
                return
            for path in self._prompts_dir.iterdir():
                if path.suffix not in (".yaml", ".yml", ".json"):
                    continue
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        if path.suffix == ".json":
                            data = json.load(f)
                        else:
                            data = yaml.safe_load(f)
                    if not data or not isinstance(data, dict):
                        logger.warning("Skipping %s: empty or invalid format", path.name)
                        continue
                    prompt_name = data.get("name", path.stem)
                    data["_source_file"] = path.name
                    self._cache[prompt_name] = data
                    logger.debug("Loaded prompt: %s (v%s)", prompt_name, data.get("version", "?"))
                except Exception as exc:
                    logger.warning("Failed to load %s: %s", path.name, exc)
            self._loaded = True

    def reload(self) -> None:
        """Clear cache and reload all prompts from disk."""
        with self._lock:
            self._cache.clear()
            self._loaded = False
        self._load_all()

    def get_prompt(self, prompt_name: str, version: str = "latest") -> Dict[str, Any]:
        """Retrieve a prompt by name.

        Args:
            prompt_name: Prompt identifier.
            version: Semantic version to retrieve, or "latest".

        Returns:
            Prompt data dict with keys: name, version, description,
            template, variables, tags.

        Raises:
            PromptNotFoundError: If no prompt with that name exists.
        """
        self._load_all()
        if prompt_name not in self._cache:
            available = sorted(self._cache.keys())
            raise PromptNotFoundError(
                f"Prompt '{prompt_name}' not found. Available: {available}"
            )
        data = dict(self._cache[prompt_name])
        if version != "latest" and data.get("version") != version:
            logger.warning(
                "Prompt '%s' version '%s' requested but only '%s' available",
                prompt_name, version, data.get("version"),
            )
        data.pop("_source_file", None)
        return data

    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all available prompts with metadata.

        Returns:
            List of dicts with keys: name, version, description, tags.
        """
        self._load_all()
        results = []
        for prompt_name, data in sorted(self._cache.items()):
            results.append({
                "name": prompt_name,
                "version": data.get("version", "unversioned"),
                "description": data.get("description", ""),
                "tags": data.get("tags", []),
            })
        return results

    def render_prompt(self, prompt_name: str, version: str = "latest", **kwargs: Any) -> str:
        """Retrieve a prompt and substitute variables into its template.

        Args:
            prompt_name: Prompt identifier.
            version: Semantic version to retrieve, or "latest".
            **kwargs: Variable values for template substitution.

        Returns:
            Rendered prompt string with variables filled in.

        Raises:
            PromptNotFoundError: If no prompt with that name exists.
            PromptRenderError: If a required variable is missing.
        """
        data = self.get_prompt(prompt_name, version=version)
        template = data.get("template", "")
        required = data.get("variables", [])
        missing = [v for v in required if v not in kwargs]
        if missing:
            raise PromptRenderError(
                f"Prompt '{prompt_name}' missing required variables: {missing}"
            )
        try:
            return template.format(**kwargs)
        except KeyError as exc:
            raise PromptRenderError(
                f"Template variable {exc} not provided for prompt '{prompt_name}'"
            ) from exc


_default_registry = PromptRegistry()


def get_prompt(prompt_name: str, version: str = "latest") -> Dict[str, Any]:
    """Retrieve a prompt by name from the default registry."""
    return _default_registry.get_prompt(prompt_name, version=version)


def list_prompts() -> List[Dict[str, Any]]:
    """List all available prompts from the default registry."""
    return _default_registry.list_prompts()


def render_prompt(prompt_name: str, version: str = "latest", **kwargs: Any) -> str:
    """Render a prompt with variables from the default registry."""
    return _default_registry.render_prompt(prompt_name, version=version, **kwargs)
