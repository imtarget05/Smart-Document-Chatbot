"""
Tests for the centralized prompt management system.

Tests cover prompt loading, variable substitution, missing prompt handling,
version selection, and registry operations.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prompts import get_prompt, list_prompts, render_prompt, PromptRegistry
from prompts.registry import PromptNotFoundError, PromptRenderError


@pytest.fixture
def registry():
    """Create a PromptRegistry instance using the default prompts directory."""
    prompts_dir = Path(__file__).parent.parent / "prompts" / "prompts"
    return PromptRegistry(prompts_dir=prompts_dir)


@pytest.fixture
def temp_prompts_dir():
    """Create a temporary directory with test prompt files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)

        # Valid YAML prompt
        yaml_prompt = {
            "name": "test_greeting",
            "version": "1.0.0",
            "description": "A test greeting prompt",
            "template": "Hello, {name}! Welcome to {place}.",
            "variables": ["name", "place"],
            "tags": ["test", "greeting"],
        }
        with open(prompts_dir / "test_greeting.yaml", "w") as f:
            yaml.dump(yaml_prompt, f)

        # Valid JSON prompt
        json_prompt = {
            "name": "test_farewell",
            "version": "2.0.0",
            "description": "A test farewell prompt",
            "template": "Goodbye, {name}! See you on {day}.",
            "variables": ["name", "day"],
            "tags": ["test", "farewell"],
        }
        with open(prompts_dir / "test_farewell.json", "w") as f:
            import json as json_mod
            json_mod.dump(json_prompt, f)

        # Prompt with version 2
        yaml_v2 = {
            "name": "versioned_prompt",
            "version": "2.0.0",
            "description": "Version 2 of a prompt",
            "template": "Version 2: {value}",
            "variables": ["value"],
            "tags": ["test"],
        }
        with open(prompts_dir / "versioned_prompt.yaml", "w") as f:
            yaml.dump(yaml_v2, f)

        yield prompts_dir


class TestPromptRegistry:
    """Tests for PromptRegistry class."""

    def test_load_all_prompts(self, registry):
        """Test that all prompts are loaded from the prompts directory."""
        prompts = registry.list_prompts()
        names = [p["name"] for p in prompts]
        assert "rag_answer" in names
        assert "orchestrator_intent" in names
        assert "query_reformulation" in names
        assert "entity_extraction" in names
        assert "report_generation" in names

    def test_get_prompt_returns_data(self, registry):
        """Test that get_prompt returns the expected data structure."""
        prompt = registry.get_prompt("rag_answer")
        assert prompt["name"] == "rag_answer"
        assert prompt["version"] == "1.0.0"
        assert "template" in prompt
        assert "variables" in prompt
        assert "tags" in prompt

    def test_get_prompt_latest_version(self, registry):
        """Test that version='latest' returns the prompt."""
        prompt = registry.get_prompt("rag_answer", version="latest")
        assert prompt["name"] == "rag_answer"

    def test_get_prompt_specific_version(self, registry):
        """Test that a specific version can be requested."""
        prompt = registry.get_prompt("rag_answer", version="1.0.0")
        assert prompt["version"] == "1.0.0"

    def test_get_prompt_nonexistent_raises(self, registry):
        """Test that requesting a nonexistent prompt raises PromptNotFoundError."""
        with pytest.raises(PromptNotFoundError) as exc_info:
            registry.get_prompt("nonexistent_prompt")
        assert "nonexistent_prompt" in str(exc_info.value)

    def test_list_prompts_returns_metadata(self, registry):
        """Test that list_prompts returns metadata for all prompts."""
        prompts = registry.list_prompts()
        assert len(prompts) >= 5
        for p in prompts:
            assert "name" in p
            assert "version" in p
            assert "description" in p
            assert "tags" in p

    def test_render_prompt_substitutes_variables(self, registry):
        """Test that render_prompt substitutes variables correctly."""
        result = registry.render_prompt(
            "query_reformulation", query="What is Python?"
        )
        assert "What is Python?" in result
        assert "Rewrite the following question" in result

    def test_render_prompt_missing_variable_raises(self, registry):
        """Test that missing required variables raise PromptRenderError."""
        with pytest.raises(PromptRenderError) as exc_info:
            registry.render_prompt("query_reformulation")
        assert "missing" in str(exc_info.value).lower()

    def test_render_prompt_with_extra_variables(self, registry):
        """Test rendering with all required variables provided."""
        result = registry.render_prompt(
            "rag_answer",
            query="test query",
            context="test context",
            history_text="",
            extra_section="",
        )
        assert "test query" in result
        assert "test context" in result


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    def test_module_get_prompt(self):
        """Test module-level get_prompt function."""
        prompt = get_prompt("rag_answer")
        assert prompt["name"] == "rag_answer"

    def test_module_list_prompts(self):
        """Test module-level list_prompts function."""
        prompts = list_prompts()
        assert len(prompts) >= 5

    def test_module_render_prompt(self):
        """Test module-level render_prompt function."""
        result = render_prompt("query_reformulation", query="test")
        assert "test" in result


class TestCustomRegistry:
    """Tests for PromptRegistry with custom directories."""

    def test_custom_directory_loading(self, temp_prompts_dir):
        """Test loading prompts from a custom directory."""
        reg = PromptRegistry(prompts_dir=temp_prompts_dir)
        prompts = reg.list_prompts()
        names = [p["name"] for p in prompts]
        assert "test_greeting" in names
        assert "test_farewell" in names

    def test_yaml_and_json_loaded(self, temp_prompts_dir):
        """Test that both YAML and JSON files are loaded."""
        reg = PromptRegistry(prompts_dir=temp_prompts_dir)
        greeting = reg.get_prompt("test_greeting")
        farewell = reg.get_prompt("test_farewell")
        assert greeting["name"] == "test_greeting"
        assert farewell["name"] == "test_farewell"

    def test_render_from_custom_dir(self, temp_prompts_dir):
        """Test rendering a prompt from a custom directory."""
        reg = PromptRegistry(prompts_dir=temp_prompts_dir)
        result = reg.render_prompt("test_greeting", name="Alice", place="Wonderland")
        assert "Hello, Alice!" in result
        assert "Welcome to Wonderland" in result

    def test_missing_prompt_in_custom_dir(self, temp_prompts_dir):
        """Test error handling for missing prompt in custom directory."""
        reg = PromptRegistry(prompts_dir=temp_prompts_dir)
        with pytest.raises(PromptNotFoundError):
            reg.get_prompt("nonexistent")

    def test_missing_variable_in_custom_dir(self, temp_prompts_dir):
        """Test error handling for missing variables in custom directory."""
        reg = PromptRegistry(prompts_dir=temp_prompts_dir)
        with pytest.raises(PromptRenderError):
            reg.render_prompt("test_greeting", name="Alice")

    def test_reload_clears_cache(self, temp_prompts_dir):
        """Test that reload clears the cache and reloads prompts."""
        reg = PromptRegistry(prompts_dir=temp_prompts_dir)
        reg.get_prompt("test_greeting")
        reg.reload()
        prompt = reg.get_prompt("test_greeting")
        assert prompt["name"] == "test_greeting"

    def test_nonexistent_directory(self):
        """Test behavior when prompts directory doesn't exist."""
        reg = PromptRegistry(prompts_dir=Path("/nonexistent/path"))
        prompts = reg.list_prompts()
        assert prompts == []


class TestPromptFiles:
    """Tests for the actual prompt YAML files."""

    def test_rag_answer_has_required_variables(self, registry):
        """Test that rag_answer prompt defines all required variables."""
        prompt = registry.get_prompt("rag_answer")
        assert "query" in prompt["variables"]
        assert "context" in prompt["variables"]

    def test_orchestrator_intent_has_query_variable(self, registry):
        """Test that orchestrator_intent prompt has query variable."""
        prompt = registry.get_prompt("orchestrator_intent")
        assert "query" in prompt["variables"]

    def test_entity_extraction_has_conversation_text_variable(self, registry):
        """Test that entity_extraction prompt has conversation_text variable."""
        prompt = registry.get_prompt("entity_extraction")
        assert "conversation_text" in prompt["variables"]

    def test_report_generation_has_required_variables(self, registry):
        """Test that report_generation prompt has title and content variables."""
        prompt = registry.get_prompt("report_generation")
        assert "title" in prompt["variables"]
        assert "content" in prompt["variables"]

    def test_all_prompts_have_versions(self, registry):
        """Test that all prompts have semantic versions."""
        prompts = registry.list_prompts()
        for p in prompts:
            assert p["version"] != "unversioned", f"Prompt {p['name']} has no version"

    def test_all_prompts_have_tags(self, registry):
        """Test that all prompts have tags for categorization."""
        prompts = registry.list_prompts()
        for p in prompts:
            assert len(p["tags"]) > 0, f"Prompt {p['name']} has no tags"
