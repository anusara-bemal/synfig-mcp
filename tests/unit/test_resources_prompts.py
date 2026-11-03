# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Anusara Bemal (ABM)
"""Tests for MCP resources and prompts."""

from __future__ import annotations

import json

import pytest
from tests.conftest import ToolBox


def payload(raw: str) -> dict:
    return json.loads(raw)


@pytest.fixture
def resources(server):  # type: ignore[no-untyped-def]
    return server._resource_manager._resources


@pytest.fixture
def templates(server):  # type: ignore[no-untyped-def]
    return server._resource_manager._templates


@pytest.fixture
def prompts(server):  # type: ignore[no-untyped-def]
    return server._prompt_manager


class TestResources:
    async def test_projects(self, resources, project: str) -> None:
        data = payload(await resources["synfig://projects"].fn())
        assert any(item["project_id"] == project for item in data["projects"])

    async def test_project_info(self, templates, project: str) -> None:
        fn = templates["synfig://project/{project_id}/info"].fn
        info = payload(await fn(project_id=project))
        assert info["project_id"] == project
        assert info["width"] == 256

    async def test_project_layers(self, templates, project: str, tools: ToolBox) -> None:
        await tools.add_circle(project_id=project, name="dot")
        fn = templates["synfig://project/{project_id}/layers"].fn
        data = payload(await fn(project_id=project))
        assert data["layers"][0]["name"] == "dot"

    async def test_project_xml(self, templates, project: str) -> None:
        fn = templates["synfig://project/{project_id}/xml"].fn
        xml = await fn(project_id=project)
        assert "<canvas" in xml
        assert "demo" in xml

    async def test_missing_project(self, templates) -> None:
        info = payload(await templates["synfig://project/{project_id}/info"].fn(project_id="nope"))
        assert info["error"] == "project_not_found"
        xml = await templates["synfig://project/{project_id}/xml"].fn(project_id="nope")
        assert xml.startswith("<!-- error:")
        layers = payload(
            await templates["synfig://project/{project_id}/layers"].fn(project_id="nope")
        )
        assert layers["error"] == "project_not_found"

    async def test_layer_type_docs(self, resources) -> None:
        data = payload(await resources["synfig://docs/layer-types"].fn())
        assert data["count"] >= 10
        assert "circle" in data["layer_types"]


class TestPrompts:
    def test_all_prompts_registered(self, prompts) -> None:
        names = {prompt.name for prompt in prompts.list_prompts()}
        assert names == {
            "create_logo_animation",
            "create_explainer_scene",
            "rig_character",
            "loop_gif",
            "fix_broken_project",
        }

    @pytest.mark.parametrize(
        ("name", "argument", "needle"),
        [
            ("create_logo_animation", {"logo_description": "a blue star"}, "a blue star"),
            ("create_explainer_scene", {"topic": "tides"}, "tides"),
            ("rig_character", {"character_description": "a cat"}, "a cat"),
            ("loop_gif", {"subject": "a wheel"}, "a wheel"),
            ("fix_broken_project", {"path": "broken.sif"}, "broken.sif"),
        ],
    )
    def test_prompt_text(self, prompts, name: str, argument: dict, needle: str) -> None:
        text = prompts.get_prompt(name).fn(**argument)
        assert needle in text
        assert "synfig-mcp" in text or "Synfig Studio" in text

    def test_prompt_defaults(self, prompts) -> None:
        text = prompts.get_prompt("create_logo_animation").fn()
        assert "simple geometric mark" in text
