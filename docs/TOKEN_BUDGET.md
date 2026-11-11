# Synfig MCP Token Budget Baseline

> **Phase A0 Baseline Audit** (Target: v0.8.0-rc1)
> Measured with OpenAI `cl100k_base` and `o200k_base` tokenizers (`tiktoken v0.14.0`)
> Vision model calculations use published tile formulas for OpenAI (detail=high/low), Claude, and Gemini.

## 1. `tools/list` Token Budget & Profile Ceilings

- **Default Profile (`all`)**: 80 tools, 74,339 bytes, **20,087 tokens** (`cl100k_base`).
- **Minimal Profile (`core`)**: 13 tools, 11,262 bytes, **2,984 tokens** (`cl100k_base`).

> [!NOTE]
> The server ships with the complete `all` profile enabled by default. Clients with a
> tight context budget can switch to `core`, which reduces the initial system prompt payload
> from **20,087 tokens** to **2,984 tokens**.

### Profile Allocations & Measured Counts

| Profile (`SYNFIG_MCP_PROFILE`) | Tool Count | Measured Tokens (`cl100k`) | Measured Tokens (`o200k`) | Status vs Ceiling |
|---|---|---|---|---|
| `core` | 13 | **2,984** | 2,991 | ✅ Pass (< 3000) |
| `anim` | 21 | **5,158** | 5,164 | ❌ Exceeds (4500) |
| `fx` | 25 | **5,900** | 5,907 | ❌ Exceeds (4500) |
| `rig` | 22 | **5,101** | 5,112 | ❌ Exceeds (3000) |
| `assets` | 12 | **2,682** | 2,687 | ❌ Exceeds (2000) |
| `review` | 18 | **4,904** | 4,915 | ❌ Exceeds (4000) |
| `all` | 80 | **20,087** | 20,111 | ❌ Exceeds (16000) |

---

## 2. Response Size of Top 15 Common Calls

Measured against real server output in headless mode:

| Tool Invocation | Response Chars | `cl100k_base` Tokens | `o200k_base` Tokens | Token Budget Ceiling |
|---|---|---|---|---|
| `health_check()` | 298 | **96** | 97 | < 200 |
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
| `render_frame(160x120)` | 138 | **53** | 53 | < 200 |
| `schema_list_layers()` | 11 | **2** | 2 | < 200 |
| `schema_get_layer(circle)` | 1683 | **454** | 453 | < 908 |

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
| `render_sequence` | 1,544 | **445** | 445 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `canvas_set_properties` | 1,468 | **413** | 413 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `doc_set_properties` | 1,380 | **405** | 405 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_start` | 1,351 | **390** | 390 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_contact_sheet` | 1,332 | **380** | 380 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_video` | 1,298 | **377** | 377 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `anim_waypoint_set` | 1,228 | **338** | 336 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_frame` | 1,174 | **335** | 336 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `layer_add` | 1,195 | **332** | 332 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `review_compare` | 1,152 | **328** | 330 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `review_frame` | 1,126 | **324** | 324 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `review_sequence` | 1,139 | **319** | 319 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `param_convert` | 1,133 | **312** | 314 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `recipe_apply` | 1,147 | **309** | 310 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `doc_set_time_range` | 1,055 | **298** | 299 | Move detailed guidance to synfig://guide/ and trim enum descriptions |

---

## 5. Token Baseline CI Enforcement

Enforced via `server/tests/unit/test_token_budget.py`.
- Asserts `tools/list` total tokens do not exceed the baseline without profile gating.
- Asserts typical single tool call responses stay strictly below 500 tokens.
