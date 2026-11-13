"""
Story bible and screenplay models for the anime production pipeline (Phase 5).

Pre-production needs a *continuity bible* (who, where, what, when) and a
*screenplay* (scenes, shots, dialogue, timing) that every later stage can trust.
This module defines those as plain Pydantic data, and provides a deterministic
*compiler* that derives them from a :class:`~synfig_mcp.production.models.ProductionBrief`.

Honesty note: the server has no language model, so it does not invent stories.
:func:`compile_story` is a structural compiler - it summarises the brief's own
shots, characters, background and assets into a consistent bible and marks the
result ``authored=False``.  Creative writing (a real logline, character bios,
scene breaks) is the client's job: an LLM can call the ``story_bible`` tool,
edit the returned bible and pass it back through ``ProductionBrief.story``; the
pipeline then validates it, sets ``authored=True`` and consumes it unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids an import cycle
    from synfig_mcp.production.models import ProductionBrief

#: The id used for the single location the compiler derives from the background.
DERIVED_LOCATION_ID = "loc_main"

#: File name of the persisted bible inside a production's output directory.
STORY_FILENAME = "story_bible.json"


class StoryCharacter(BaseModel):
    """One character as tracked by the bible."""

    id: str = Field(description="Matches a ProductionBrief character id.")
    name: str = Field(default="", description="Display name; empty when the brief has none.")
    role: str = Field(
        default="supporting", description="'protagonist', 'supporting' or 'antagonist'."
    )
    archetype: str = Field(default="humanoid", description="Proportion preset.")
    wardrobe: list[str] = Field(
        default_factory=list, description="Palette / costume colours carried from the descriptor."
    )
    bio: str = Field(default="", description="One-line description (derived or authored).")


class StoryLocation(BaseModel):
    """A place the story happens in."""

    id: str
    name: str
    description: str = ""


class StoryProp(BaseModel):
    """A tracked object that must stay consistent across scenes."""

    id: str
    description: str = ""


class StoryRelationship(BaseModel):
    """A continuity link between two characters."""

    source: str = Field(description="Character id.")
    target: str = Field(description="Character id.")
    kind: str = Field(default="acquaintance", description="e.g. 'sibling', 'rival', 'mentor'.")


class TimelineBeat(BaseModel):
    """A point on the story timeline, in seconds."""

    time: float = Field(ge=0.0)
    label: str


class StoryScene(BaseModel):
    """A scene: a slugline plus the shots, characters and dialogue it contains."""

    scene_id: str
    slugline: str = Field(default="", description="Screenplay heading, e.g. 'EXT. ROOFTOP - DAY'.")
    location: str = Field(default=DERIVED_LOCATION_ID, description="A StoryLocation id.")
    time_of_day: str = Field(default="day")
    summary: str = ""
    characters: list[str] = Field(default_factory=list, description="Character ids present.")
    dialogue: list[dict[str, str]] = Field(
        default_factory=list, description="[{'character': id, 'line': text}]."
    )
    shots: list[str] = Field(default_factory=list, description="StoryboardShot ids in this scene.")


class StoryBible(BaseModel):
    """The continuity bible the pipeline persists and later stages consume."""

    authored: bool = Field(
        default=False,
        description="True when a client supplied this bible; False when the server derived it.",
    )
    logline: str = ""
    synopsis: str = ""
    characters: list[StoryCharacter] = Field(default_factory=list)
    locations: list[StoryLocation] = Field(default_factory=list)
    props: list[StoryProp] = Field(default_factory=list)
    relationships: list[StoryRelationship] = Field(default_factory=list)
    timeline: list[TimelineBeat] = Field(default_factory=list)
    scenes: list[StoryScene] = Field(default_factory=list)


class Screenplay(BaseModel):
    """A read-only, flattened view of the bible for reporting and tooling."""

    title: str
    logline: str
    synopsis: str
    authored: bool = False
    scenes: list[StoryScene] = Field(default_factory=list)
    shot_count: int = 0
    total_duration: float = 0.0


def _shot_list(brief: ProductionBrief) -> list[Any]:
    """The brief's shots, or a single implicit shot spanning the whole duration."""
    if brief.shots:
        return list(brief.shots)
    from synfig_mcp.characters.models import StoryboardShot

    return [
        StoryboardShot(
            shot_id="shot_01",
            description=f"{brief.title} - single continuous shot",
            duration_seconds=brief.duration,
        )
    ]


def _derive_characters(brief: ProductionBrief) -> list[StoryCharacter]:
    characters: list[StoryCharacter] = []
    for index, descriptor in enumerate(brief.characters):
        role = "protagonist" if index == 0 else "supporting"
        characters.append(
            StoryCharacter(
                id=descriptor.id,
                role=role,
                archetype=descriptor.archetype,
                wardrobe=list(descriptor.palette),
                bio=f"{descriptor.archetype} character ({role}).",
            )
        )
    return characters


def _derive_locations(brief: ProductionBrief) -> list[StoryLocation]:
    generator = None
    if isinstance(brief.background, dict):
        generator = brief.background.get("generator")
    name = str(generator).replace("_", " ").title() if generator else "Studio"
    return [
        StoryLocation(
            id=DERIVED_LOCATION_ID,
            name=name,
            description=f"Derived from the background ({generator or 'default'}).",
        )
    ]


def _derive_props(brief: ProductionBrief) -> list[StoryProp]:
    props: list[StoryProp] = []
    for request in brief.assets:
        if request.kind != "prop":
            continue
        if request.procedural:
            detail = str(request.procedural.get("generator", "procedural"))
        elif request.search:
            detail = str(request.search.get("query", "search"))
        else:  # pragma: no cover - validated upstream
            detail = "prop"
        props.append(StoryProp(id=request.id, description=detail))
    return props


def _derive_timeline(shots: list[Any]) -> list[TimelineBeat]:
    beats: list[TimelineBeat] = []
    clock = 0.0
    for shot in shots:
        beats.append(TimelineBeat(time=round(clock, 3), label=shot.shot_id))
        clock += shot.duration_seconds
    return beats


def _derive_scene(shots: list[Any], location_id: str) -> StoryScene:
    characters = sorted({cid for shot in shots for cid in shot.characters_present})
    dialogue = [{"character": "narrator", "line": shot.dialogue} for shot in shots if shot.dialogue]
    return StoryScene(
        scene_id="scene_01",
        slugline=f"EXT. {location_id.upper()} - DAY",
        location=location_id,
        summary=" ".join(shot.description for shot in shots).strip(),
        characters=characters,
        dialogue=dialogue,
        shots=[shot.shot_id for shot in shots],
    )


def compile_story(brief: ProductionBrief) -> StoryBible:
    """Derive a consistent story bible from a brief.

    When the brief already carries an authored bible (``brief.story``) it is
    returned unchanged, so the client's creative work is never overwritten.
    """
    if brief.story is not None:
        if isinstance(brief.story, StoryBible):
            return brief.story
        return StoryBible.model_validate(brief.story)

    shots = _shot_list(brief)
    characters = _derive_characters(brief)
    locations = _derive_locations(brief)
    props = _derive_props(brief)
    location_id = locations[0].id if locations else DERIVED_LOCATION_ID

    names = ", ".join(c.id for c in characters) or "no characters"
    total = round(sum(shot.duration_seconds for shot in shots), 3)
    logline = (
        f"A {brief.style} piece titled '{brief.title}': {len(shots)} shot(s) over "
        f"{total:.1f}s featuring {names}."
    )
    synopsis = " ".join(shot.description for shot in shots).strip() or logline

    return StoryBible(
        authored=False,
        logline=logline,
        synopsis=synopsis,
        characters=characters,
        locations=locations,
        props=props,
        relationships=[],
        timeline=_derive_timeline(shots),
        scenes=[_derive_scene(shots, location_id)],
    )


def build_screenplay(brief: ProductionBrief, bible: StoryBible) -> Screenplay:
    """Flatten a bible into a screenplay view for reporting."""
    shots = _shot_list(brief)
    return Screenplay(
        title=brief.title,
        logline=bible.logline,
        synopsis=bible.synopsis,
        authored=bible.authored,
        scenes=list(bible.scenes),
        shot_count=len(shots),
        total_duration=round(sum(shot.duration_seconds for shot in shots), 3),
    )


def validate_story(brief: ProductionBrief, bible: StoryBible) -> list[str]:
    """Return continuity problems in a bible (empty when it is consistent).

    These are honest structural checks, not taste judgements: unknown ids,
    drift from the brief, and a timeline that does not match the shot list.
    """
    issues: list[str] = []
    shots = _shot_list(brief)
    shot_ids = [shot.shot_id for shot in shots]
    declared = {c.id for c in brief.characters}

    seen: set[str] = set()
    for character in bible.characters:
        if character.id in seen:
            issues.append(f"character '{character.id}' is declared twice")
        seen.add(character.id)
        if character.id not in declared:
            issues.append(f"bible character '{character.id}' is not in the brief")

    missing = sorted(declared - seen)
    if missing:
        issues.append(f"brief characters missing from the bible: {missing}")

    if len(bible.timeline) != len(shots):
        issues.append(f"timeline has {len(bible.timeline)} beat(s) for {len(shots)} shot(s)")

    for scene in bible.scenes:
        unknown = [sid for sid in scene.shots if sid not in shot_ids]
        if unknown:
            issues.append(f"scene '{scene.scene_id}' references unknown shots {unknown}")

    referenced = sorted({cid for shot in shots for cid in shot.characters_present})
    for cid in referenced:
        if cid not in declared:
            issues.append(f"shot references undeclared character '{cid}'")

    return issues
