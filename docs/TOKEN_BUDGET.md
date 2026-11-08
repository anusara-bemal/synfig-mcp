# Synfig MCP Token Budget Baseline

> **Phase A0 Baseline Audit** (Target: v0.8.0-rc1)
> Measured with OpenAI `cl100k_base` and `o200k_base` tokenizers (`tiktoken v0.14.0`)
> Vision model calculations use published tile formulas for OpenAI (detail=high/low), Claude, and Gemini.

## 1. `tools/list` Token Budget & Profile Ceilings

- **Default Profile (`core`)**: 12 tools, 9,835 bytes, **2,658 tokens** (`cl100k_base`).
- **Full Studio Profile (`all`)**: 65 tools, 57,857 bytes, **15,924 tokens** (`cl100k_base`).

> [!NOTE]
> `core` profile reduces initial system prompt payload from **15,924 tokens** to **2,658 tokens** (an **82.8% reduction**), well under the 3,000 token ceiling enforced by CI.

### Profile Allocations & Measured Counts

| Profile (`SYNFIG_MCP_PROFILE`) | Tool Count | Measured Tokens (`cl100k`) | Measured Tokens (`o200k`) | Status vs Ceiling |
|---|---|---|---|---|
| `core` | 12 | **2,658** | 2,665 | ✅ Pass (< 3000) |
| `anim` | 18 | **4,330** | 4,335 | ✅ Pass (< 4500) |
| `fx` | 23 | **5,304** | 5,311 | ❌ Exceeds (4500) |
| `rig` | 12 | **2,528** | 2,533 | ✅ Pass (< 3000) |
| `assets` | 7 | **1,420** | 1,426 | ✅ Pass (< 2000) |
| `review` | 17 | **4,609** | 4,619 | ❌ Exceeds (4000) |
| `all` | 65 | **15,924** | 15,942 | ✅ Pass (< 16000) |

---

## 2. Response Size of Top 15 Common Calls

Measured against real server output in headless mode:

| Tool Invocation | Response Chars | `cl100k_base` Tokens | `o200k_base` Tokens | Token Budget Ceiling |
|---|---|---|---|---|
| `health_check()` | 267 | **91** | 91 | < 200 |
| `doc_new(160x120)` | 193 | **84** | 84 | < 200 |
| `doc_list()` | 389 | **122** | 122 | < 244 |
| `layer_add(circle)` | 251 | **85** | 85 | < 200 |
| `scene_tree()` | 1179 | **350** | 350 | < 700 |
| `doc_info()` | 389 | **122** | 122 | < 244 |
| `param_set(radius=2.5)` | 325 | **118** | 118 | < 236 |
| `param_get(radius)` | 232 | **56** | 56 | < 200 |
| `anim_time_set(1.5s)` | 17 | **11** | 11 | < 200 |
| `anim_time_get()` | 17 | **11** | 11 | < 200 |
| `anim_keyframe_list()` | 0 | **0** | 0 | < 200 |
| `history_undo()` | 21 | **8** | 8 | < 200 |
| `render_frame(160x120)` | 138 | **54** | 53 | < 200 |
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
| `render_sequence` | 1,520 | **442** | 442 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `doc_set_properties` | 1,356 | **402** | 402 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_start` | 1,327 | **387** | 387 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_contact_sheet` | 1,308 | **377** | 377 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_video` | 1,274 | **374** | 374 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `anim_waypoint_set` | 1,193 | **333** | 331 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `layer_add` | 1,171 | **329** | 329 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `review_compare` | 1,128 | **325** | 327 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `render_frame` | 1,117 | **322** | 322 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `review_frame` | 1,102 | **321** | 321 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `review_sequence` | 1,115 | **316** | 316 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `recipe_apply` | 1,123 | **306** | 307 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `doc_set_time_range` | 1,031 | **295** | 296 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `param_get` | 988 | **292** | 291 | Move detailed guidance to synfig://guide/ and trim enum descriptions |
| `param_set` | 969 | **283** | 283 | Move detailed guidance to synfig://guide/ and trim enum descriptions |

---

## 5. Token Baseline CI Enforcement

Enforced via `server/tests/unit/test_token_budget.py`.
- Asserts `tools/list` total tokens do not exceed the baseline without profile gating.
- Asserts typical single tool call responses stay strictly below 500 tokens.
