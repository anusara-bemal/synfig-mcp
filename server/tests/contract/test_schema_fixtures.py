"""
Validate every JSON fixture in protocol/fixtures/ against protocol/schema/*.json.
"""

import json
from pathlib import Path

import pytest
from jsonschema import validate


@pytest.fixture
def repo_root() -> Path:
    # server/tests/contract/ -> server/tests/ -> server/ -> repo_root
    return Path(__file__).resolve().parent.parent.parent.parent


def test_fixtures_against_json_schemas(repo_root: Path) -> None:
    schema_dir = repo_root / "protocol" / "schema"
    fixtures_dir = repo_root / "protocol" / "fixtures"

    assert schema_dir.is_dir()
    assert fixtures_dir.is_dir()

    requests_schema = json.loads((schema_dir / "requests.json").read_text(encoding="utf-8"))
    responses_schema = json.loads((schema_dir / "responses.json").read_text(encoding="utf-8"))
    events_schema = json.loads((schema_dir / "events.json").read_text(encoding="utf-8"))

    # Test requests
    request_fixtures = [
        "handshake_request.json",
        "doc_info_request.json",
        "layer_add_request.json",
        "param_set_request.json",
    ]
    for rf in request_fixtures:
        fixture_path = fixtures_dir / rf
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        validate(instance=data, schema=requests_schema)

    # Test responses
    response_fixtures = [
        "handshake_response.json",
        "doc_info_response.json",
        "layer_add_response.json",
        "param_set_response.json",
    ]
    for rf in response_fixtures:
        fixture_path = fixtures_dir / rf
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        validate(instance=data, schema=responses_schema)

    # Test events
    event_fixtures = [
        "event_time_changed.json",
        "event_selection_changed.json",
    ]
    for ef in event_fixtures:
        fixture_path = fixtures_dir / ef
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        validate(instance=data, schema=events_schema)
