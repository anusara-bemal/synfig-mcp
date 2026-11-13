# Synfig MCP Token Budget Baseline

> **Phase A0 Baseline Audit** (Target: v0.8.0-rc1)
> Measured with OpenAI `cl100k_base` and `o200k_base` tokenizers (`tiktoken v0.14.0`)
> Vision model calculations use published tile formulas for OpenAI (detail=high/low), Claude, and Gemini.

## 1. `tools/list` Token Budget & Profile Ceilings

- **Default Profile (`all`)**: 105 tools, 101,831 bytes, **27,781 tokens** (`cl100k_base`).
- **Minimal Profile (`core`)**: 20 tools, 17,294 bytes, **4,603 tokens** (`cl100k_base`).

> [!NOTE]
> The server ships with the complete `all` profile enabled by default. Clients with a
> tight context budget can switch to `core`, which reduces the initial system prompt payload
> from **27,781 tokens** to **4,603 tokens**.

### Profile Allocations & Measured Counts

| Profile (`SYNFIG_MCP_PROFILE`) | Tool Count | Measured Tokens (`cl100k`) | Measured Tokens (`o200k`) | Status vs Ceiling |
|---|---|---|---|---|
| `core` | 20 | **4,603** | 4,626 | ✅ Pass (< 5000) |
| `anim` | 28 | **6,742** | 6,765 | ❌ Exceeds (4500) |
| `fx` | 32 | **7,472** | 7,496 | ❌ Exceeds (4500) |
| `rig` | 35 | **9,839** | 9,872 | ❌ Exceeds (3000) |
| `assets` | 24 | **6,466** | 6,485 | ❌ Exceeds (2000) |
| `review` | 25 | **6,497** | 6,525 | ❌ Exceeds (4000) |
| `all` | 105 | **27,781** | 27,848 | ✅ Pass (< 28000) |

---

## 2. Response Size of Top 15 Common Calls

Measured against real server output in headless mode:

| Tool Invocation | Response Chars | `cl100k_base` Tokens | `o200k_base` Tokens | Token Budget Ceiling |
|---|---|---|---|---|
| `health_check()` | 256 | **77** | 78 | < 200 |
| `doc_new(160x120)` | 193 | **84** | 84 | < 200 |
| `doc_list()` | 389 | **122** | 122 | < 244 |
| `layer_add(circle)` | 251 | **85** | 85 | < 200 |
| `scene_tree()` | 1228 | **363** | 363 | < 726 |
| `doc_info()` | 389 | **122** | 122 | < 244 |
| `param_set(radius=2.5)` | 325 | **118** | 118 | < 236 |
| `param_get(radius)` | 232 | **56** | 56 | < 200 |
| `anim_time_set(1.5s)` | 17 | **11** | 11 | < 200 |
| `anim_time_get()` | 17 | **11** | 11 | < 200 |
| `anim_keyframe_list()` | 0 | **0** | 0 | < 200 |
| `history_undo()` | 21 | **8** | 8 | < 200 |
| `render_frame(160x120)` | 103 | **43** | 43 | < 200 |
| `schema_list_layers()` | 11 | **2** | 2 | < 200 |
| `schema_get_layer(circle)` | 2662 | **720** | 719 | < 1440 |

---

## 3. Vision Preview Image Token Model

Vision model consumption per single preview or contact-sheet image:

| Resolution & Use Case | Pixels | Claude 3/3.5 (`px/750`) | Gemini 1.5/2.0 (`258/tile`) | OpenAI Detail=High | OpenAI Detail=Low |
|---|---|---|---|---|---|
| **160x120 (Thumbnail / Icon)** | 19,200 | 26 | 258 | 255 | 85 |
| **320x240 (Quick review / Iteration)** | 76,800 | 103 | 258 | 255 | 85 |
| **480x270 (16:9 SD preview)** | 129,600 | 173 | 258 | 255 | 85 |
| **640x480 (Standard preview)** | 307,200 | 410 | 258 | 425 | 85 |
| **960x540 (High-detail half-HD)** | 518,400 | 692 | 516 | 765 | 85 |
| **1280x720 (720p HD frame)** | 921,600 | 1229 | 516 | 1105 | 85 |
| **1920x1080 (1080p full frame)** | 2,073,600 | 2765 | 1548 | 1105 | 85 |
| **640x640 (2x2 Contact sheet - 4 frames)** | 409,600 | 547 | 258 | 765 | 85 |
| **960x960 (3x3 Contact sheet - 9 frames)** | 921,600 | 1229 | 1032 | 765 | 85 |

### Visual Review Loop Optimization Takeaways

1. **Quick Iteration Default**: `320x240` consumes only **103 Claude tokens** / **258 Gemini tokens** / **255 OpenAI tokens** while providing sufficient visual fidelity to detect layout, clipping, and motion errors.
2. **Contact Sheet Efficiency**: A 4-frame `640x640` contact sheet costs **547 Claude / 516 Gemini / 765 OpenAI tokens**, whereas rendering 4 individual 640x480 frames costs **1,640 Claude / 1,032 Gemini / 3,060 OpenAI tokens** (a **3x to 4x token reduction**).
3. **Zoom-In Crops**: Use targeted 320x240 crops on detected violation regions instead of full 1080p frame re-renders.

---

## 4. Top 15 Heaviest Tool Definitions (`tools/list`)

| Tool Name | Schema Size (chars) | `cl100k_base` Tokens | `o200k_base` Tokens | Optimization Target in A1 |
|---|---|---|---|---|
| `rig_sheet_from_image` | 2,661 | **731** | 732 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `scene_auto_build` | 1,695 | **483** | 483 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `rig_sheet_slice` | 1,638 | **464** | 466 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `produce_anime_project` | 1,750 | **455** | 455 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_sequence` | 1,520 | **442** | 442 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `character_motion_apply` | 1,525 | **436** | 436 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `sprite_slice` | 1,461 | **416** | 417 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `canvas_set_properties` | 1,444 | **410** | 410 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `doc_set_properties` | 1,356 | **402** | 402 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `rig_bone_add` | 1,276 | **389** | 389 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `procedural_asset_generate` | 1,372 | **389** | 386 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_start` | 1,327 | **387** | 387 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_contact_sheet` | 1,308 | **377** | 377 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_video` | 1,274 | **374** | 374 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `character_pose_apply` | 1,250 | **347** | 348 | Move detailed guidance to synfig://guide/ and trim enum descriptions |

---

## 5. Token Baseline CI Enforcement

Enforced via `server/tests/unit/test_token_budget.py`.
- Asserts `tools/list` total tokens do not exceed the baseline without profile gating.
- Asserts typical single tool call responses stay strictly below 500 tokens.
