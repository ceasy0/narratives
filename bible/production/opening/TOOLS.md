# The Opening — tools research

> The research behind the [production plan](./PLAN.md): faces without a scan, expressions from a webcam, Blender 5, GPU shaders and fractal renderers, AI video and its prices, image models on 8 GB, and how studios catch pacing and staging problems. Gathered 2026-10-13, with a source for each point. Prices and versions move fast; re-check before spending money.

Confidence marks: [H] verified from an official or primary source, [M] from a reputable secondary source or partly verified, [U] unverified or inferred.
Target machine: Windows, RTX 2060 Super 8 GB (Turing), 32 GB RAM, Blender 5.0, Python 3.14, ffmpeg.

---

## 1. Designed realistic faces without a scan, usable in Blender

### MetaHuman (Epic)
- Since MetaHuman 5.6 (June 2025), Creator, Mesh to MetaHuman and Animator run **inside Unreal Engine** instead of the cloud web app. Autorigging and texture synthesis still call cloud services, so you need an internet connection. [H] https://metahuman.com/news/metahuman-leaves-early-access-with-a-feature-packed-new-release · [M] https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/
- The old web Creator is being wound down. One blog gives Nov 5 2026 as the final shutdown date. [U, single non-Epic source] https://www.strayspark.studio/blog/metahuman-2026-web-app-shutdown-migration-guide (this blog also says the licence is UE-only, which contradicts Epic's own pages, so treat it as unreliable).
- **Licence:** Epic's page says "MetaHumans can be used with any engine or creative software". Use falls under the standard UE EULA. It is free under $1M/yr revenue, and above that you need UE seats (about $1,850/yr). Using MetaHumans in AI-incorporating workflows is allowed, but they **must not be used to train or improve AI models**. [H] https://www.metahuman.com/license?lang=en-US · [M] https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/
  - In practice, rendering a MetaHuman in Blender for a non-commercial or under-$1M series is allowed. The remaining risk: feeding MetaHuman renders into AI video models (e.g. as Veo/Kling first frames) could be read as "enhancing AI models". Normal reading is inference, not training, but check the EULA text before doing it. [U]
- **Export to Blender:** The in-UE "DCC Export" writes **head DNA + body DNA + textures** (.dna/.png/.json zip). Epic names Maya and Houdini as targets, not Blender, and the export includes no FBX. [H] https://dev.epicgames.com/documentation/metahuman/metahuman-creator-export-tool-in-unreal-engine
  - Blender bridge: Poly Hammer **"Character DNA"** (formerly MetaHuman DNA add-on). It imports head.dna/body.dna, animates the face board and skeleton, bakes, and writes back to DNA. Supports UE 5.6/5.7 DNA and Blender 4.5/5.0, and v0.10.3 adds Blender 5.2. The base edition **went free (GPLv3) in July 2026**. Pro editors cost $79 perpetual. Because of the UE EULA you compile it yourself with their build tool. Still in beta. [M] https://digitalproduction.com/2026/07/22/character-dna-goes-free/ · https://www.cgchannel.com/2026/03/metahuman-dna-add-on-for-blender-gets-new-rbf-editor/
  - Another option is Skalin MetaMorph (DNA to Blender to FBX/DNA), free beta. [M] https://forums.unrealengine.com/t/metahuman-dcc-blender-or-fbx-export/2544434/3
- **Hardware:** Epic's *recommended* spec is a 16-core CPU, 32 GB RAM, and an RTX 3070-class GPU with 8 GB VRAM. The 2060 Super is below the recommended GPU tier, but **no MetaHuman-specific minimum is listed**. Animator needs DX12. So the 2060 Super is likely usable but slow. [H for spec, U for "usable"] https://dev.epicgames.com/documentation/metahuman/metahuman-hardware-requirements-in-unreal-engine
- **MetaHuman Animator from mono video/webcam:** Supported **since MetaHuman 5.6 / UE 5.6**: real-time and offline from most webcams and many phones via LiveLink, plus audio-only animation. [H] https://metahuman.com/news/metahuman-leaves-early-access-with-a-feature-packed-new-release. The mono-video docs also mention an *experimental* markerless body/face-and-body plugin in UE 5.8 (Windows only). [H] https://dev.epicgames.com/documentation/metahuman/metahuman-animation-from-mono-video-capture-in-unreal-engine
  - Route: record a webcam performance, solve it in UE with MetaHuman Animator, bake the animation, then bring it to Blender (via DNA/face-board curves). Alternatively render the face in UE directly. The UE-to-Blender animation round trip has the most moving parts in the whole pipeline. [U]

### MPFB2 (MakeHuman Plugin for Blender)
- Free. The plugin is GPLv3, bundled assets are **CC0**, and **content you make is CC0** (commercial use OK). [M] https://www.cgchannel.com/2025/03/check-out-open-source-blender-character-generation-plugin-mpfb-2
- MPFB 2.0.16 (June 13 2026) adds **52 ARKit-compatible face units** (`faceunits01` asset pack) and an expression composer that drives shape keys. [H] https://static.makehumancommunity.org/mpfb/releases/release_2016.html
- Realism: stylised/mid-realism out of the box, with lower skin, pore and eye fidelity than MetaHuman or CC5. Needs custom skin shading to approach photoreal. [U, general knowledge]

### Reallusion Character Creator 5 + Headshot 3
- **CC5 costs $299 perpetual** or $29/mo / $99/yr. **Headshot 3.1 costs $199**, and the Headshot 1400+ morph pack is $99. [M] https://www.cgchannel.com/2026/07/reallusion-releases-headshot-3-0/
- Headshot 3 builds a head from **one photo** with a local AI model, and can also take an AI-generated photo (its own Nano-Banana image generator, about $0.30/image). This means a "designed" face without scanning him: generate a face image, then Headshot, then CC5. [M] same source
- CC has an established Blender bridge (CC/iC Blender Tools) and ARKit-style expression sets. [U, not verified this session]

### KeenTools FaceBuilder for Blender
- Builds a head from photos (even one image). Comes with **51 ARKit-compatible FACS blendshapes** and supports Live Link Face. **Freelancer plans cost $15.99/mo billed yearly ($191.88/yr) or $19.99 monthly.** The FaceBuilder+FaceTracker bundle is $24.99/mo yearly. [H] https://keentools.io/products/facebuilder-for-blender
- Topology and skin are good for likeness, but it is a mesh plus textures, not a full skin/eye/hair character system. [U]

### Open image-to-3D generators (TRELLIS.2, Hunyuan3D 2.1, TripoSR, Stable Fast 3D)
- None output **rigged faces or blendshapes**. Most need more than 8 GB (TRELLIS.2 needs 12–16 GB with offload; the full Hunyuan3D 2.1 pipeline needs about 29 GB, its mini version 3–6 GB; TripoSR needs 6–8 GB). They aren't useful for an expressive hero face. [M] https://trellis2.app/blog/best-image-to-3d-models-huggingface

### Verdict for Q1
- **Most realistic face plus expression rig for least money: MetaHuman (free)**, made in UE 5.6+/5.7 Creator and brought to Blender via DNA with Character DNA (free base). Risks: UE install size, 2060 Super below the recommended spec, the DNA-to-Blender round trip is beta, and the AI-model clause in the licence.
- **Simplest all-in-Blender route: MPFB2 + faceunits (free, CC0)** plus a custom skin shader. Lower realism, zero licence friction, and fully scriptable by the agent.
- **Middle route ($498): CC5 + Headshot 3** from an AI-generated portrait. Highly realistic, with a mature Blender bridge.

---

## 2. Driving expressions from his own webcam video (no scan)

- **MediaPipe Face Landmarker** outputs **52 blendshape scores** (ARKit-named) plus a facial transformation matrix (head pose). It has a VIDEO running mode for decoded frames. [H] https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker
- `mediapipe` 1.1.0 (Oct 6 2026) has Windows wheels, and its classifiers list Python 3.9–3.14. It can run on his Python 3.14 but should go in its own venv, not Blender's Python. [H] https://pypi.org/project/mediapipe/
- **Pipeline (free, scriptable):** webcam MP4 → Python+MediaPipe → per-frame CSV/JSON of 52 weights + head matrix → Blender script keys shape keys of the same names (MPFB faceunits, FaceBuilder, Faceit-generated, or a MetaHuman face board via mapping) → smoothing (One-Euro/Butterworth) + per-channel gain curves. [U, standard practice]
  - Known limitation: MediaPipe blendshapes are noisier and less nuanced than iPhone TrueDepth or MetaHuman Animator. Expect to hand-amplify the extremes (terror, wild laugh). [U]
- **Faceit** (Blender add-on): generates the 52 ARKit shape keys on any face mesh and imports Live Link Face CSV, Face Cap TXT, and Audio2Face JSON. It also has live receivers. **$78 (1.8 ARKit) / $99 (2.3)**, Blender 3.0–5.2. [H] https://superhivemarket.com/products/faceit
  - No native webcam support. The docs point to the third-party **"Face Landmark Link"** app (MediaPipe) that writes Live Link Face-format CSV from video/webcam. [H] https://faceit-doc.readthedocs.io/en/latest/mocap_general/
- **AI Face (Superhive), $29.99:** webcam-only, 24 of 52 ARKit shapes, Blender 2.8–4.0. Outdated for Blender 5. [H] https://superhivemarket.com/products/ai-face-markerless-facial-mocap-for-blender
- **KeenTools FaceTracker for Blender** (bundle $24.99/mo yearly): video face tracking with ARKit blendshapes. Higher quality than raw MediaPipe, paid. [H for bundle price] https://keentools.io/products/facebuilder-for-blender
- **MetaHuman Animator mono** (free, in UE 5.6+): highest quality from a webcam, but only drives MetaHuman rigs in UE. See Q1. [H]
- **Verdict:** Free and agent-scriptable: MediaPipe → CSV → Blender shape keys. Best quality: MetaHuman Animator mono. Optional $78–99 for Faceit to generate and clean shape keys on a custom head.

---

## 3. Blender 5.0 / 5.x facts

- Blender 5.0 released **Nov 20 2025**. Highlights: ACES/HDR colour management, OpenVDB **volume grid** sockets in GN, SDF nodes, new Cycles null-scattering volumes, a Compositor modifier in the VSE, and new compositor Chromatic Aberration + Sensor Noise nodes. [M] https://digitalproduction.com/2025/11/20/blender-5-0-its-here/
- 5.1 (Mar 2026): more GN volume features, a Raycast shader node (NPR), and Python 3.13. [M] https://alternativeto.net/news/2026/3/3d-software-blender-5-1-refines-key-workflows-boosts-performance-and-expands-geometry-nodes
- 5.2 LTS (Jul 14 2026): **experimental GN-based physics (cloth, hair)**, GN lists and functions, an EEVEE screen-space ray-tracing cleanup (scenes may render darker than 5.1), and faster instancing. [M] https://linuxiac.com/?p=215993 · darker note: [M] https://app.cinevva.com/guides/blender-5-for-game-artists
- **Geometry Nodes 5.0:** Bundles, **Closures**, volume grids (Advect Grid, curl/divergence/gradient, SDF fillet/offset, Grid to Mesh). [H] https://developer.blender.org/docs/release_notes/5.0/geometry_nodes/
  - Simulation zones date from 3.6 [M] https://betanews.com/2023/06/28/blender-3-6/. Repeat zones date from 4.0 [M] https://www.blendernation.com/2023/11/14/blender-4-0-released-check-out-the-new-features-of-blenders-new-era/. Both are available in 5.0.
- **Shader repeat zones (new in 5.0):** shader nodes can loop. **EEVEE supports dynamic iteration counts. Cycles needs a fixed count and unrolls it** (compile/runtime cost). This is directly useful for Mandelbrot/Julia shaders in EEVEE without OSL. [H] https://developer.blender.org/docs/release_notes/5.0/rendering/
- **Cycles OSL on GPU:** OSL works on **CPU and OptiX** (since 3.5). OptiX limitations: no `trace()` (AO/Bevel), no cell/simplex/Gabor noise, and texture paths must be constant. Loops are fine. The 2060 Super (Turing RTX) supports OptiX. [H] https://docs.blender.org/manual/en/latest/render/shader_nodes/osl.html · https://blogs.nvidia.com/blog/blender-3-5-release
- **Cycles 5.0:** default unbiased null-scattering volumes (old "Biased" mode still available), NanoVDB for smoke/fire, minimum NVIDIA compute is sm_50 (Turing is fine), and OSL camera aperture is a breaking change. [H] https://developer.blender.org/docs/release_notes/5.0/cycles/
- **EEVEE (Next, since 4.2):** screen-space ray tracing for all BSDFs, world volumes can block sun/background, and mesh volumes intersect properly. Volumes are still froxel-based, and object/world volumes aren't captured by light probes. [H] https://developer.blender.org/docs/release_notes/4.2/eevee
  - 5.0: engine ID is now `BLENDER_EEVEE` (was `BLENDER_EEVEE_NEXT`). `gtao_distance` moved to the view layer as `ambient_occlusion_distance`. Curve/hair resolution is now respected (about 15x more geometry for default hair, a VRAM risk on 8 GB). Faster material compile on NVIDIA. [H] https://developer.blender.org/docs/release_notes/5.0/eevee/
- **Render speed on 2060 Super:** Blender Open Data score is about **1,443** (CUDA, 3.5). For reference: Classroom about 66 s, Junkshop about 46 s per frame. An RTX 4090 is about 8x faster. [M] https://www.renderjuice.com/gpus/rtx-2060-super-for-blender
  - Implication [U]: 5 min at 24 fps is 7,200 frames. Cycles at about 30–60 s/frame is 60–120 h. EEVEE at about 2–10 s/frame is 4–20 h. Use EEVEE for most beats and Cycles only where volumes or refraction need it.
- **Python API breaks in 5.0 that matter for scripts:** [M] https://app.cinevva.com/guides/blender-5-for-game-artists · [M] https://github.com/LuxCoreRender/BlendLuxCore/issues/1049
  - `scene.node_tree` was removed, use `scene.compositing_node_group` (compositor is now a node-group asset).
  - `action.fcurves` / `action.groups` were removed (slotted actions). Use `bpy_extras.anim_utils.action_ensure_channelbag_for_slot()` and then `channelbag.fcurves`. `keyframe_insert()` still works.
  - `material/world/scene.use_nodes` are deprecated (always node-based).
  - Dict-style access to RNA props (`scene['cycles']`) no longer works.
  - `bgl` and `Image.bindcode` were removed (use `gpu`).
  - `BLENDER_EEVEE_NEXT` became `BLENDER_EEVEE`.
  - Point Density texture removed. Render pass names changed (e.g. "DiffCol" became "Diffuse Color"). [H] https://developer.blender.org/docs/release_notes/5.0/rendering/
  - 5.2 changes the GN modifier input API (`modifier["Socket_2"]` → `modifier.properties.inputs.<id>.value`). [M] cinevva source above
  - mathutils precision changes. [M] BlendLuxCore issue
  - The full official Python API page (developer.blender.org/docs/release_notes/5.0/python_api/) couldn't be fetched from this sandbox. [U for completeness]

---

## 4. GPU shaders outside Blender (fractals, particle fields) to image sequences

- **moderngl 5.13.0** (Oct 7 2026), wheels for CPython 3.9–3.15 (so Python 3.14 is fine). Headless use: `moderngl.create_context(standalone=True)`, with WGL as the default backend on Windows and the `moderngl[headless]` extra via glcontext. Requires OpenGL 3.3+, and you can ask for 4.3 for compute shaders with `require=430`. Render to an FBO, read pixels, write PNG/EXR, then ffmpeg. [H] https://moderngl.readthedocs.io/en/latest/topics/context.html · https://pypi.org/project/moderngl/
  - This is the best fit for agent-driven fractal/particle passes: deterministic, fast on the 2060 Super, and easy to drive from a script. Double-precision limits a GLSL Mandelbrot zoom to about 1e-13 without perturbation. [U, standard numerical fact]
- **TouchDesigner Non-Commercial:** free, **1280x1280 max resolution**, no paid work ("not receiving money or compensation"), some operators missing. A bad fit for a 1080p/4K series deliverable. [H] https://derivative.ca/UserGuide/TouchDesigner_Non-Commercial
- **Kalles Fraktaler 2+** (Windows, **AGPLv3+**; latest kf-2.15.5.2, 2022): deep zooms with perturbation. Renders "zoom-out" keyframe sequences (KFB/EXR) that are assembled into video. [H] https://mathr.co.uk/kf/kf.html
  - **zoomasm 3.4** (Jun 2025, AGPLv3+): assembles KF exponential-map EXR keyframes into zoom video via FFmpeg (MP4/MKV/MOV or PPM sequence). Colouring is a GLSL fragment, so the look is fully controllable. Needs OpenGL 3.3+ and about 8 GB RAM/VRAM recommended. Windows builds are untested by the author. [H] https://mathr.co.uk/zoomasm/
  - fraktaler-3 (same author) has OpenCL GPU support and exports KF/zoomasm-compatible EXR. [H] https://mathr.co.uk/kf/kf.html
- **Mandelbulber2:** GPLv3, Windows/Linux/macOS, multi-GPU OpenCL, keyframe animation for all parameters, a CLI for headless use, and a render queue (writes frame sequences). Best for 3D fractal fly-throughs, and the agent can script it via CLI + settings files. [H] https://github.com/buddhi1980/mandelbulber2
- **Mandelbulb3D:** LGPL-2.1, Windows, no restrictions. Keyframe animation with linear/Bézier interpolation and renders frames, with resume ("Start with index"). GUI-driven, so harder for an agent to automate. [H] https://github.com/thargor6/mb3d
- **Inside Blender instead:** use the 5.0 shader repeat zone (EEVEE, dynamic iterations) or OSL on OptiX for a Mandelbrot texture on a plane or volume. See Q3.

---

## 5. AI video for live-action-looking placeholder shots

Prices are official per-second API rates unless noted.

| Model | $/s | Max length / control | Notes | Conf. |
|---|---|---|---|---|
| **Veo 3.1** (Google) | $0.40 (720p/1080p), $0.60 (4K), with audio | 4/6/8 s. **First + last frame** (`image` + `lastFrame`), up to 3 reference images, extend +7 s ×20 up to 148 s (720p) | personGeneration for image-to-video, interpolation and reference images is `allow_adult` only. SynthID watermark | [H] https://ai.google.dev/gemini-api/docs/veo · https://ai.google.dev/gemini-api/docs/pricing |
| Veo 3.1 Fast | $0.10 (720p), $0.12 (1080p), $0.30 (4K) | same controls | best value for iteration | [H] same |
| Veo 3.1 Lite | $0.05 (720p), $0.08 (1080p) | no extension, no reference images | | [H] same |
| Veo via Runway API | $0.20/s without audio, $0.10/s Fast without audio | | sound is his own, so no-audio is the right choice | [H] https://docs.dev.runwayml.com/guides/pricing/ |
| **Sora 2 / Sora 2 Pro** | $0.10 / $0.70 | 4–20 s | **OpenAI deprecated the entire Videos API and Sora models; removed Sep 24 2026. Not available now.** | [M] https://help.make.com/openai-sora-and-video-modules-deprecation-by-september-24-2026 · https://invideo.io/blog/ai-video-model-pricing |
| **Kling 3.0** | about $0.18–0.24/s silent (Krea API std/pro), $0.44 4K. Official Kling 3.0 Turbo is ¥0.8/s (about $0.11) at 720p | 3–15 s, **start_image + end_image**, multi-prompt "multi-shot" | | [M] https://www.krea.ai/blog/kling-3-0-api-access-guide-pricing-code-examples-for-multi-shot-ai-video · https://invideo.io/blog/ai-video-model-pricing |
| **Runway Gen-4.5** | $0.12 | text/image-to-video | first/last-frame support not confirmed in docs | [H price] https://docs.dev.runwayml.com/guides/models/ |
| Runway Gen-4 Turbo | $0.05 | image-to-video | | [H] same |
| **Runway Aleph 2.0** (video-to-video restyle) | $0.28 (min $0.56/job) | "keyframe-guided" video editing | **Best fit for restyling Blender renders into live-action-looking plates** | [H] https://docs.dev.runwayml.com/guides/pricing/ |
| **Luma Ray 3.2** | 720p $0.30/5 s, 1080p $1.20/5 s ($0.06–0.24/s). Video edit 1080p $2.16/5 s | 5/10 s blocks, keyframe extend | HDR/EXR option | [H] https://docs.agents.lumalabs.ai/guides/pricing/ |
| Hailuo (MiniMax H3) | $0.13 | | | [M] invideo |
| LTX-2.3 (API) | $0.06–0.32 | | | [M] invideo |

- **Open weights, local on 8 GB:**
  - **Wan 2.2 TI2V-5B**: ComfyUI docs say it "should fit well on 8GB vram with ComfyUI native offloading". 1280×704, about 5 s clips. Slow on a 2060 Super (a 4090 takes under 9 min for 5 s at 720p, so expect 30+ min) [U for 2060 timing]. [H] https://docs.comfy.org/tutorials/video/wan/wan2_2 · [M] https://localaimaster.com/blog/wan-vram-requirements-by-gpu
  - **Wan 2.2 14B FLF2V (first-last frame)** exists in ComfyUI, but 14B on 8 GB means GGUF Q4 + heavy offload and is "very slow". [H for FLF2V] [M for 8 GB]
  - Wan 2.1 1.3B: 480p, the lightest. The newest *open* Wan is 2.2. Wan 2.5/2.6 are API-only, and "Wan 2.7 download" sites are fakes. [M] localaimaster source
  - **LTX-2.x**: licence free for commercial use under $10M revenue [H] https://ltx.io/model/license. Official local guidance is 16 GB (LTX-2.3 per NVIDIA) to 32 GB+ (LTX-2.5 per LTX). Community GGUFs exist, but **8 GB is not officially supported** [H] https://www.nvidia.com/en-gb/geforce/news/rtx-ai-video-generation-guide · https://ltx.io/model/model-blog/run-video-generation-model-locally. Has First/Last-frame templates.
  - Turing (20-series) lacks fast FP8/bf16 paths, so quantized models run slower than on 30/40-series. [U]
- **Content policy (violence / child burial):**
  - Runway bans "graphic violence… towards humans or animals" and gore (dismemberment, exposed organs), and applies tighter rules whenever a child appears. [H] https://runway.com/safety/usage-policy
  - Veo: blocks prompts that violate guidelines and runs output safety filters. Image-to-video with people is limited to `allow_adult` (so a **child in an input frame may be refused**). [H] https://ai.google.dev/gemini-api/docs/veo. The specific violence categories couldn't be fetched. [U]
  - Kling: policy page not fetched. [U]
  - Practical inference [U]: a non-graphic big-cat fight (no blood), a tribal clash in silhouette or wide shot, and a burial with a wrapped body and no visible child face will mostly pass. Close, bloody or child-focused shots are likely to be blocked. Plan to do these in Blender or with local Wan, which has no filter.
- **Cost estimate [U]:** for 5 min (300 s) of footage at roughly a 4:1 generate-to-keep ratio, about 1,200 s generated. At Veo 3.1 Fast 1080p ($0.12) that is about $144. At Kling Pro (about $0.24) about $290. At Veo 3.1 standard ($0.40) about $480. Only beats 10–14 need live-action AI. Abstract beats are rendered procedurally.

---

## 6. ComfyUI on 8 GB VRAM (concept frames, restyling Blender renders)

- **SDXL**: 1024×1024 single image is the realistic 8 GB target. Use tiled VAE (512/64) and batch 1. **Each ControlNet adds about 2–3 GB**, so SDXL + one ControlNet (depth or canny) fits, but stacking Hires Fix + 2 ControlNets + FaceDetailer can OOM. [M] https://eastondev.com/blog/en/posts/ai/20260721-comfyui-low-vram-acceleration/
- **FLUX.1-dev GGUF**: Q4_K_S (6.8 GB) or Q5_K_S (8.5 GB) are "edge cases" on 8 GB. About 90–150 s/image on a 3060 Ti 8 GB, so slower on a 2060 Super. Use a T5 in fp8/GGUF. FLUX.1-dev weights are **non-commercial**. [M] eastondev · [M licence] https://www.nvidia.com/en-gb/geforce/news/rtx-ai-video-generation-guide
- **FLUX.2 Klein 4B**: **Apache 2.0**, text-to-image + multi-reference editing. Official fit is about 13 GB VRAM. The GGUF Q4_K_M is about 2.6 GB and runs in 15–30 s on 8 GB (4 steps). **Best modern choice for 8 GB with a clean licence.** [H licence/VRAM] https://huggingface.co/black-forest-labs/FLUX.2-klein-4B · [M speed] eastondev
- **Z-Image Turbo** (FP8 about 5.8 GB): runs even on 6 GB, but needs about 25–28 GB of system RAM. Photoreal. [M] https://discuss.huggingface.co/t/running-modern-ai-image-models-on-a-gtx-1060-6gb-a-practical-guide/176079
- Launch flags: `--reserve-vram 2`, `--preview-method none`, fp8 text encoder. [M] eastondev
- **Restyle Blender renders:** Blender outputs beauty + depth (Z/mist) + line/canny passes. Feed them to SDXL ControlNet depth+canny, or to FLUX.2 Klein reference editing, per keyframe. For moving shots, use Runway Aleph or Wan v2v instead of per-frame img2img, which flickers. [U, standard practice]

---

## 7. Professional pipeline practice (solo/small team)

- **Standard stages:** script → storyboard → **editorial / animatic (story reel) with temp sound** → previz/**layout** (real cameras, lenses, blocking) → look-dev/assets → animation → lighting/FX → render → comp/colour → **picture lock** → final sound/score to locked picture. Blender Studio's pipeline lists Pre-production (Storyboard, **Editorial**, **Previz**, Concept), Asset creation, and Shot production (Shot Assembly, **Layout**, Animation, Lighting, Effects, Rendering, Coloring). [H] https://studio.blender.org/tools/pipeline-overview/introduction
- **Edit as the spine:** Blender Studio builds a rough animatic in the VSE, with one colour strip per shot giving position and duration. Each shot's strip is then **replaced in place** by boards → layout → playblast → final render, so the film is always watchable at full length. [H] https://studio.blender.org/tools/pipeline-overview/pre-production/editorial
- **Pacing lock:** the animatic is timed with temp sound/music until scenes don't drag. Then "no new story beats or changes to the overall timing should occur after this point". It becomes the master reference for frame counts. [M] https://animation.binus.ac.id/2025/12/09/animatic-creation-and-pacing-lock/
- **How staging/spatial errors are caught:** **layout** places characters and props, picks lenses, shot sizes and camera paths, sets camera timing, and tracks continuity across shots. It catches continuity errors, unclear staging, and **scale errors (characters covering impossible distances, floating props)**, using grey "flat pass" previews before animation. [M] https://pixune.com/blog/layout-in-3d-animation/
- Previs "tells you exactly where you're going to be, and exactly what you're going to see" (Disney). Rough layout should be integrated with story early. Otherwise teams only discover late whether story and environments fit. [M] https://www.awn.com/vfxworld/previs-bridging-gap-between-animation-and-live-action
- **Shot list columns:** scene #, shot #, description, shot size, angle, movement, **lens/focal length**, equipment, frame rate, cast, notes. Pair it with a **floor plan / overhead diagram** of camera, lights and actors. [M] https://www.studiobinder.com/blog/how-to-make-a-shot-list/
- **Implications for this project [U]:**
  1. Lock the story-reel timing first, with his held-note temp track, before any polish. The "leaf falls too fast" note is exactly a story-reel timing fix.
  2. Write a shot list with duration, lens, camera move, and subject path per shot. Draw an overhead map per set (forest, cliff, Nile delta) showing camera and subject paths.
  3. Do a grey-box layout pass in Blender, rendered as fast EEVEE/Workbench playblasts, and cut it into the VSE in place of the boards.
  4. Only then do look-dev and final renders. Score in FL Studio to picture lock (export a locked reference MP4 with burned-in timecode and frame numbers).
