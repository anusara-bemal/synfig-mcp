# Synfig MCP Token Budget Baseline

> **Phase A0 Baseline Audit** (Target: v0.8.0-rc1)
> Measured with OpenAI `cl100k_base` and `o200k_base` tokenizers (`tiktoken v0.14.0`)
> Vision model calculations use published tile formulas for OpenAI (detail=high/low), Claude, and Gemini.

## 1. `tools/list` Token Budget & Profile Ceilings

- **Current Total Tools**: 52 tools exposed simultaneously in a single default profile.
- **Current Raw JSON Size**: 55,967 bytes (75,011 formatted).
- **Current Baseline Token Cost**: **15,498 tokens** (`cl100k_base`) / **15,506 tokens** (`o200k_base`).

> [!WARNING]
> Without tool profiles, an LLM agent consumes **15,498 tokens** on its very first turn just loading the tool definitions,
> before executing a single animation command. Phase A1 introduces profiles to cap the default tool definition payload under **3,000 tokens**.

### Projected Phase A1 Profile Allocations

| Profile (`SYNFIG_MCP_PROFILE`) | Tool Count | Target Token Ceiling (`cl100k`) | Target Description |
|---|---|---|---|
| `core` (default) | ~12 | **< 3,000 tokens** | Health, doc lifecycle, layer CRUD, time, status |
| `anim` | ~10 | **< 2,500 tokens** | Waypoints, keyframes, time ranges, timetrack |
| `fx` | ~8 | **< 2,000 tokens** | Recipe library, filters, composites, grading |
| `rig` | ~8 | **< 2,000 tokens** | Cut-out skeletons, bone binding, parts assembly |
| `assets` | ~6 | **< 1,500 tokens** | Openverse/Wikimedia search, download, attribution |
| `review` | ~6 | **< 1,500 tokens** | Frame critique, SSIM diff, strobe/safe-area check |
| `all` | 52 | 15,498 tokens | Complete unconstrained studio suite |

---

## 2. Response Size of Top 15 Common Calls

Measured against real server output in headless mode:

| Tool Invocation | Response Chars | `cl100k_base` Tokens | `o200k_base` Tokens | Token Budget Ceiling |
|---|---|---|---|---|
| `health_check()` | 267 | **91** | 91 | < 200 |
| `doc_new(160x120)` | 193 | **83** | 83 | < 200 |
| `doc_list()` | 389 | **121** | 121 | < 242 |
| `layer_add(circle)` | 251 | **84** | 84 | < 200 |
| `scene_tree()` | 1179 | **349** | 349 | < 698 |
| `doc_info()` | 389 | **121** | 121 | < 242 |
| `param_set(radius=2.5)` | 325 | **117** | 117 | < 234 |
| `param_get(radius)` | 232 | **56** | 56 | < 200 |
| `anim_time_set(1.5s)` | 17 | **11** | 11 | < 200 |
| `anim_time_get()` | 17 | **11** | 11 | < 200 |
| `anim_keyframe_list()` | 0 | **0** | 0 | < 200 |
| `history_undo()` | 21 | **8** | 8 | < 200 |
| `render_frame(160x120)` | 138 | **54** | 54 | < 200 |
| `schema_list_layers()` | 11 | **2** | 2 | < 200 |
| `schema_get_layer(circle)` | 1388 | **386** | 385 | < 772 |

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
| `render_sequence` | 1,905 | **551** | 550 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `doc_set_properties` | 1,557 | **465** | 465 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_video` | 1,507 | **446** | 446 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `layer_add` | 1,491 | **440** | 440 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_contact_sheet` | 1,542 | **440** | 440 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `anim_waypoint_set` | 1,519 | **425** | 422 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_start` | 1,462 | **418** | 419 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_frame` | 1,341 | **386** | 386 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `anim_animate_param` | 1,371 | **385** | 387 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `doc_set_time_range` | 1,235 | **358** | 359 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `param_set` | 1,213 | **357** | 356 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `param_get` | 1,214 | **354** | 353 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `param_convert` | 1,250 | **347** | 350 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `anim_interpolation_set` | 1,246 | **332** | 332 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `layer_reorder` | 1,156 | **327** | 327 | Move detailed guidance to synfig://guide/ and trim enum descriptions |

---

## 5. Token Baseline CI Enforcement

Enforced via `server/tests/unit/test_token_budget.py`.
- Asserts `tools/list` total tokens do not exceed the baseline without profile gating.
- Asserts typical single tool call responses stay strictly below 500 tokens.
