"""The series' painted look (Discussion 006, round 4): Arcane's method, with our own designs, in
Blender's EEVEE. Imported by the style tests (face_test.py, band_mocap_test.py -- painted).

What makes the look, and where each part of it is here:

- Light painted, not rendered smoothly. Each material reads how much light reaches it (a white
  diffuse surface, through Shader to RGB) and turns from shadow to half-tone to light in three
  painted values, each turn a sharp edge broken by the brushstrokes; it paints its own colours
  either side: warm in the light, a cooler, richer colour in the shadow, never grey. paint()
- Paint that's dry and matte, defined rather than smooth (your notes, 2026-10-15): the colour
  drifts in big soft patches, then lies in flat dabs of a few values with edges, under a fine
  dry grain; creases are painted dark; nothing shines but what's wet. On the mesh's own UVs (so
  it stays put on a moving body) or its object space. paint(coords=..., dabs=..., crease=...)
- A faint cool edge on the lit side, and a small hard highlight where something is wet.
  paint(rim=..., spec=...)
- A thin dark line round the characters. outline()
- A painted sky, seen only by the camera; the light it gives the scene is a dim, even fill. sky()
- Air over the whole frame: distance fades toward the haze colour, and a light anisotropic
  Kuwahara filter ties the strokes together without smoothing the shapes away. finish()
- Real brush strokes, for the characters (the style test's face, accepted 2026-10-16): each
  surface's colour, its creases and its form's hollows baked into its own texture (bake), painted
  over stroke by stroke by brush.py, and the paint lit live by the renderer, its light turned into
  the painter's colours, cast shadows and all (live_mat). The strokes stay on the surface as it
  moves. Used by face_test.py and band_mocap_test.py -- painted.

Colours are given as they'd be picked on screen (sRGB) and converted here.
"""
import time

import bpy
import numpy as np


def srgb(c):
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)


class Nodes:
    """Building a node tree by hand: each call adds a node and wires what it's given. An input
    is a number, a tuple, or another node's output socket."""

    def __init__(self, nt):
        self.nt = nt

    def set(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, sock)
        elif v is not None:
            if isinstance(v, tuple):              # a colour into a vector, or the other way round
                v = (v + (1.0,) * 4)[:len(sock.default_value)]
            sock.default_value = v

    def new(self, kind, inputs=(), **props):
        n = self.nt.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        for key, v in (inputs.items() if isinstance(inputs, dict) else enumerate(inputs)):
            self.set(n.inputs[key], v)
        return n

    def math(self, op, a, b=None, c=None):
        return self.new("ShaderNodeMath", [a, b, c], operation=op).outputs[0]

    def remap(self, x, a0, a1, b0, b1, smooth=True):
        n = self.new("ShaderNodeMapRange", [x, a0, a1, b0, b1], data_type='FLOAT',
                     interpolation_type='SMOOTHSTEP' if smooth else 'LINEAR')
        n.clamp = True
        return n.outputs[0]

    def mix(self, fac, a, b, blend='MIX'):
        n = self.new("ShaderNodeMix", data_type='RGBA', blend_type=blend)
        self.set(n.inputs[0], fac)
        self.set(n.inputs[6], a if not isinstance(a, tuple) or len(a) == 4 else (*a, 1.0))
        self.set(n.inputs[7], b if not isinstance(b, tuple) or len(b) == 4 else (*b, 1.0))
        return n.outputs[2]

    def scale(self, col, f):
        """A colour times a number (or a colour times a colour, when f is a tuple or a colour)."""
        if isinstance(f, tuple) or (isinstance(f, bpy.types.NodeSocket) and f.type in ('RGBA', 'VECTOR')):
            return self.new("ShaderNodeVectorMath", [col, f], operation='MULTIPLY').outputs[0]
        n = self.new("ShaderNodeVectorMath", operation='SCALE')
        self.set(n.inputs[0], col)
        self.set(n.inputs[3], f)
        return n.outputs[0]

    def bw(self, col):
        return self.new("ShaderNodeRGBToBW", [col]).outputs[0]

    def noise(self, vec, scale, detail=2.0, rough=0.5, distort=0.0):
        return self.new("ShaderNodeTexNoise", {"Vector": vec, "Scale": scale, "Detail": detail,
                                               "Roughness": rough, "Distortion": distort}).outputs["Fac"]


def material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m, Nodes(nt), nt.nodes.new("ShaderNodeOutputMaterial")


def paint(name, base, *, shadow=(0.5, 0.4, 0.55), light=(1.0, 0.97, 0.9), coords='UV', scale=1.0,
          vary=0.1, strokes=1.0, edge=(0.16, 0.34), hard=0.035, half=0.22, half_mix=0.55,
          lit_range=(0.34, 1.6), rim=(0.58, 0.72, 1.0), rim_amount=0.08, spec=0.0,
          spec_color=(1.0, 0.95, 0.88), ao=0.35, ao_distance=0.2, crease=0.45, crease_distance=None,
          grain=0.035, dabs=4, image=None, image_mix=1.0, alpha_image=None, alpha_cut=None,
          colour=None, streaks=None, stroke=(14.0, 14.0, 46.0)):
    """A painted material, dry and matte, its shapes defined (your notes, 2026-10-15, with the
    frame of Vi from Arcane: painted, but defined).

    base: its colour (sRGB). shadow and light: what that colour is multiplied by in shadow and in
    full light; between them is a half-tone, half_mix of the way from one to the other, so a form
    turns in three painted values, not a smooth gradient. edge: where in the light (0 dark, about
    1 in full sun) the shadow turns; hard: how sharply it turns (the strokes still break the line,
    so it's a brushed edge, not a cartoon one); half: how much more light the full light needs
    (None: two values only). coords: 'UV' (bodies, which move) or 'Object' (the world). scale:
    how big the brushwork is (bigger number, smaller strokes); stroke: how the strokes stretch,
    as noise scales along x, y and z (bark wants them up the trunk); dabs: how many flat values
    the strokes come in, so they read as dabs of paint with edges; grain: a fine dry grain over
    all, as of paint on a rough ground. crease: how dark the creases are painted (eyelids,
    nostrils, the line of the lips), found by occlusion within crease_distance. image: a picture
    to take the base colour from (a skin's), mixed in by image_mix; alpha_image: one whose alpha
    cuts the surface out (hair cards, brows); colour: a function (Nodes, coords) -> colour socket
    for the base instead; streaks: (across, along) scales for strands along the UVs (hair).
    rim: a faint cool edge on the lit side; spec: a small hard highlight, for what's wet."""
    m, g, out = material(name)
    tc = g.new("ShaderNodeTexCoord")
    vec = tc.outputs[coords]
    # The base colour, drifting as paint does: big soft patches of value and a little hue...
    b = srgb(base)
    col = (*b, 1.0)
    if image is not None:
        tex = g.new("ShaderNodeTexImage", {"Vector": tc.outputs["UV"]}, image=image)
        col = g.mix(image_mix, col, tex.outputs["Color"])
    if colour is not None:
        col = colour(g, vec)
    patch = g.noise(g.scale(vec, scale), 3.0, 2.0, 0.5, 0.4)
    hue = g.noise(g.scale(vec, scale), 1.6, 1.0, 0.4, 0.2)
    col = g.mix(hue, g.scale(col, (1.04, 1.0, 0.94)), g.scale(col, (0.95, 1.0, 1.06)))
    col = g.scale(col, g.remap(patch, 0.3, 0.7, 1 - 0.6 * vary, 1 + 0.6 * vary))
    # ...then strokes laid in flat dabs with edges, and a fine dry grain.
    sv = g.new("ShaderNodeMapping", {"Vector": vec, "Scale": tuple(v * scale for v in stroke)})
    stroke_n = g.noise(sv.outputs[0], 1.0, 1.5, 0.45, 1.1)
    edge_n = g.noise(g.scale(sv.outputs[0], 3.0), 1.0, 2.0, 0.55, 0.6)       # finer, for the brushed edge of a shadow
    dab = g.math('SNAP', g.remap(stroke_n, 0.3, 0.7, 0.0, 0.999, smooth=False), 1.0 / dabs)
    col = g.scale(col, g.remap(dab, 0.0, 1.0, 1 - vary, 1 + vary, smooth=False))
    if streaks:
        st = g.new("ShaderNodeMapping", {"Vector": tc.outputs["UV"], "Scale": (streaks[0], streaks[1], 1.0)})
        strand = g.math('SNAP', g.remap(g.noise(st.outputs[0], 1.0, 2.0, 0.6, 0.3), 0.3, 0.7, 0.0, 0.999, smooth=False), 0.25)
        col = g.scale(col, g.remap(strand, 0.0, 1.0, 0.7, 1.2, smooth=False))
    if grain:
        fine = g.noise(g.scale(vec, 220.0 * scale), 1.0, 0.0, 0.5, 0.0)
        col = g.scale(col, g.remap(fine, 0.35, 0.65, 1 - grain, 1 + grain, smooth=False))
    # How much light reaches it; the turn from shadow to half-tone to light, each a brushed edge.
    dif = g.new("ShaderNodeBsdfDiffuse", {"Color": (1, 1, 1, 1)})
    lum = g.bw(g.new("ShaderNodeShaderToRGB", [dif.outputs[0]]).outputs[0])
    wob = g.math('MULTIPLY_ADD', g.math('SUBTRACT', edge_n, 0.5), 0.14 * strokes, lum)
    c0 = 0.5 * (edge[0] + edge[1])
    band = g.remap(wob, c0 - hard / 2, c0 + hard / 2, 0.0, 1.0, smooth=False)
    occ = g.new("ShaderNodeAmbientOcclusion", {"Distance": ao_distance}).outputs["AO"]
    occ = g.remap(occ, 0.0, 1.0, 1 - ao, 1.0, smooth=False)
    dark = g.scale(g.scale(col, shadow), occ)
    full = g.scale(g.scale(col, light), g.remap(lum, lit_range[0], lit_range[1], 0.95, 1.08))
    full = g.scale(full, g.remap(occ, 1 - ao, 1.0, 1 - 0.5 * ao, 1.0, smooth=False))
    if half is not None:
        lit = g.mix(g.remap(wob, c0 + half - hard / 2, c0 + half + hard / 2, 0.0, 1.0, smooth=False),
                    g.mix(half_mix, dark, full), full)
    else:
        lit = full
    c = g.mix(band, dark, lit)
    # Creases painted dark, as a painter accents them.
    if crease:
        near = g.new("ShaderNodeAmbientOcclusion", {"Distance": crease_distance or 0.35 * ao_distance}).outputs["AO"]
        cf = g.remap(near, 0.45, 0.75, crease, 0.0, smooth=False)
        c = g.mix(cf, c, g.scale(dark, 0.7))
    # A faint cool edge on the lit side only; a small hard highlight where something is wet.
    if rim_amount:
        face = g.new("ShaderNodeLayerWeight", {"Blend": 0.25}).outputs["Facing"]
        rimf = g.math('MULTIPLY', g.remap(face, 0.72, 0.8, 0.0, rim_amount, smooth=False), band)
        c = g.mix(rimf, c, (*srgb(rim), 1.0))
    if spec:
        gl = g.new("ShaderNodeBsdfGlossy", {"Color": (1, 1, 1, 1), "Roughness": 0.25})
        hi = g.remap(g.bw(g.new("ShaderNodeShaderToRGB", [gl.outputs[0]]).outputs[0]), 0.78, 0.82, 0.0, spec, smooth=False)
        c = g.mix(hi, c, (*srgb(spec_color), 1.0))
    em = g.new("ShaderNodeEmission", {"Color": c, "Strength": 1.0})
    shader = em.outputs[0]
    if alpha_image is not None:
        tex = g.new("ShaderNodeTexImage", {"Vector": tc.outputs["UV"]}, image=alpha_image)
        a = tex.outputs["Alpha"]
        if alpha_cut is not None:
            a = g.remap(a, alpha_cut - 0.05, alpha_cut + 0.05, 0.0, 1.0, smooth=False)
        tr = g.new("ShaderNodeBsdfTransparent")
        shader = g.new("ShaderNodeMixShader", [a, tr.outputs[0], shader]).outputs[0]
    g.nt.links.new(shader, out.inputs["Surface"])
    return m


def flat(name, colour):
    """A plain emitting colour: the outline, the inside of a mouth."""
    m, g, out = material(name)
    em = g.new("ShaderNodeEmission", {"Color": (*srgb(colour), 1.0), "Strength": 1.0})
    g.nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def wear(ob, m):
    """The one material on a mesh."""
    ob.data.materials.clear()
    ob.data.materials.append(m)


def node_mat(name, build):
    """A material whose surface is the shader build(Nodes) returns."""
    m, g, out = material(name)
    g.nt.links.new(build(g), out.inputs["Surface"])
    return m, g


# ---------------------------------------------------------------- real brush strokes
def bake(scene, ob, colour, size, name, folder, ao_distance=0.015, extra=(), form_distance=None, light=False,
         margin=24, samples=48):
    """Bake ob's colour (EMIT) into its UVs, with the occlusion close in (AO within ao_distance: the
    creases) and, with form_distance, wide (the form's hollows, for its painted shading); light:
    the light that reaches it too (DIFFUSE, light only), when the light is to be painted in rather
    than live. colour: a function (Nodes, uv socket) -> colour socket. extra: (kind, builder)
    pairs, more for the painter (masks, marks), each baked as the colour is. Each bake is saved in
    folder as half floats for brush.py, as name-kind.npy; returns {kind: path}. Cycles on the GPU
    (OptiX), which the scene is left set to."""
    builders = dict(extra)
    scene.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for dv in prefs.devices:
        dv.use = dv.type == 'OPTIX'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = samples
    img = bpy.data.images.new(name + " bake", size, size, float_buffer=True, alpha=False)
    out = {}
    scene.world.light_settings.distance = ao_distance
    for kind in ("base",) + (("light",) if light else ()) + ("ao",) + (("form",) if form_distance else ()) + tuple(builders):
        if kind == "base":
            m, g = node_mat(name + " base", lambda g: g.new("ShaderNodeEmission", {"Color": colour(g, g.new("ShaderNodeTexCoord").outputs["UV"]), "Strength": 1.0}).outputs[0])
        elif kind in builders:                      # the painter's masks and marks
            m, g = node_mat(name + " " + kind, lambda g: g.new("ShaderNodeEmission", {"Color": builders[kind](g), "Strength": 1.0}).outputs[0])
        else:
            m, g = node_mat(name + " " + kind, lambda g: g.new("ShaderNodeBsdfDiffuse", {"Color": (1, 1, 1, 1)}).outputs[0])
        tn = g.new("ShaderNodeTexImage", image=img)
        g.nt.nodes.active = tn
        keep = list(ob.data.materials)
        wear(ob, m)
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        t = time.time()
        if kind == "base" or kind in builders:
            bpy.ops.object.bake(type='EMIT', margin=margin, use_clear=True)
        elif kind in ("ao", "form"):                # occlusion close in: the creases; wide: the form's hollows, for its painted shading
            scene.world.light_settings.distance = ao_distance if kind == "ao" else form_distance
            bpy.ops.object.bake(type='AO', margin=margin, use_clear=True)
        else:
            bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=margin, use_clear=True)
        a = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(a)
        np.save(folder / ("%s-%s.npy" % (name, kind)), a.reshape(size, size, 4).astype(np.float16))
        out[kind] = folder / ("%s-%s.npy" % (name, kind))
        ob.data.materials.clear()
        for mm in keep:
            ob.data.materials.append(mm)
        print("baked %s %s in %.0fs" % (name, kind, time.time() - t))
    bpy.data.images.remove(img)
    return out


def live_mat(name, png, shadow, light, soft, steps=None, warm=None, sheen=0.0, quiet=None, cool=None, edge=None,
             roughness=0.42, albedo=None, alpha=None):
    """The paint lit live (your note, 2026-10-15: the real shadows): the renderer's own light on the
    surface, its cast shadows included, read as a value and turned into the painter's colours, as
    in your frame of Vi: the paint as it is in full light; deep and warm in shadow, cooler where the
    sky's fill reaches into it (cool); a short turn between (soft), warm and reddish (warm), its edge
    broken along brush strokes (edge: the stroke map and how far it moves the edge); and a second,
    gentler turn (steps), so the planes of a form facing the light less take a half-tone. sheen: a
    faint live sheen where the light catches it, none where the attribute `quiet` says. albedo: a
    colour built in nodes, (Nodes, uv) -> colour socket, instead of the painted png. alpha: (image,
    cut), a cut-out from the image's alpha (hair cards)."""
    m, g, out = material(name)
    uv = g.new("ShaderNodeTexCoord").outputs["UV"]
    if albedo:                                      # a colour built in nodes instead of a painted image
        alb = albedo(g, uv)
    else:
        alb = g.new("ShaderNodeTexImage", {"Vector": uv}, image=bpy.data.images.load(str(png))).outputs["Color"]
    lum = g.bw(g.new("ShaderNodeShaderToRGB", [g.new("ShaderNodeBsdfDiffuse", {"Color": (1, 1, 1, 1)}).outputs[0]]).outputs[0])
    raw = lum
    if edge:
        st = bpy.data.images.load(str(edge[0]), check_existing=True)
        st.colorspace_settings.name = 'Non-Color'
        n = g.bw(g.new("ShaderNodeTexImage", {"Vector": g.scale(uv, 0.5)}, image=st).outputs["Color"])   # strokes the size of a brush on screen
        lum = g.math('MULTIPLY', lum, g.math('MULTIPLY_ADD', g.math('SUBTRACT', n, 0.5), edge[1], 1.0))   # at the edge, not inside the shadow
    t = g.remap(lum, soft[0], soft[1], 0.0, 1.0)
    if steps:                                       # full light only on the planes facing it; a half-tone on the rest
        t = g.math('MULTIPLY', t, g.math('MULTIPLY_ADD', g.remap(lum, steps[0], steps[1], 0.0, 1.0), 1 - steps[2], steps[2]))
    sh = (*srgb(shadow), 1.0)
    if cool:
        sh = g.mix(g.remap(raw, cool[1], cool[2], 0.0, 1.0), sh, (*srgb(cool[0]), 1.0))
    c = g.scale(alb, g.mix(t, sh, (*srgb(light), 1.0)))
    if warm:                                        # the painter's warm note where light turns to shadow
        band = g.math('SUBTRACT', 1.0, g.math('ABSOLUTE', g.math('MULTIPLY_ADD', t, 2.0, -1.0)))
        c = g.mix(g.math('MULTIPLY', band, warm[1]), c, g.scale(c, srgb(warm[0])))
    if sheen:
        gl = g.new("ShaderNodeBsdfGlossy", {"Color": (1, 1, 1, 1), "Roughness": roughness})
        hi = g.math('MULTIPLY', g.remap(g.bw(g.new("ShaderNodeShaderToRGB", [gl.outputs[0]]).outputs[0]), 0.25, 1.2, 0.0, sheen), t)
        if quiet:
            hi = g.math('MULTIPLY', hi, g.math('SUBTRACT', 1.0, g.new("ShaderNodeAttribute", attribute_name=quiet).outputs["Fac"]))
        c = g.mix(hi, c, (*srgb((1.0, 0.95, 0.9)), 1.0), 'SCREEN')
    shader = g.new("ShaderNodeEmission", {"Color": c, "Strength": 1.0}).outputs[0]
    if alpha:
        a = g.remap(g.new("ShaderNodeTexImage", {"Vector": uv}, image=alpha[0]).outputs["Alpha"], alpha[1] - 0.05, alpha[1] + 0.05, 0.0, 1.0, smooth=False)
        shader = g.new("ShaderNodeMixShader", [a, g.new("ShaderNodeBsdfTransparent").outputs[0], shader]).outputs[0]
    g.nt.links.new(shader, out.inputs["Surface"])
    return m


_LINE = {}


def outline(ob, thickness, colour=(0.12, 0.07, 0.06)):
    """A thin dark line round a mesh: its own surface pushed out and turned inside out (the
    inverted hull), drawn only from behind."""
    key = tuple(colour)
    if key not in _LINE:
        m = flat("Outline", colour)
        m.use_backface_culling = True
        m.use_backface_culling_shadow = True
        _LINE[key] = m
    ob.data.materials.append(_LINE[key])
    sol = ob.modifiers.new("Outline", 'SOLIDIFY')
    sol.thickness = thickness
    sol.offset = 1.0
    sol.use_flip_normals = True
    sol.use_rim = False
    sol.material_offset = len(ob.data.materials) - 1
    return sol


def sky(scene, zenith=(0.36, 0.55, 0.78), horizon=(0.93, 0.84, 0.7), below=(0.45, 0.42, 0.38),
        clouds=(0.98, 0.93, 0.86), fill=(0.62, 0.7, 0.85), fill_strength=0.35, soft=0.02):
    """A painted sky for the camera, a dim even fill for the light. soft: how far below the
    horizon the sky fades into the ground colour (a backdrop with no hard line wants more)."""
    w = scene.world or bpy.data.worlds.new("Sky")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    g = Nodes(nt)
    out = g.new("ShaderNodeOutputWorld")
    d = g.new("ShaderNodeTexCoord").outputs["Generated"]
    z = g.new("ShaderNodeSeparateXYZ", [d]).outputs[2]
    up = g.mix(g.remap(z, 0.0, 0.55, 0.0, 1.0), (*srgb(horizon), 1.0), (*srgb(zenith), 1.0))
    sv = g.new("ShaderNodeMapping", {"Vector": d, "Scale": (1.6, 1.6, 5.0)})
    cl = g.remap(g.noise(sv.outputs[0], 2.2, 3.0, 0.55, 0.35), 0.52, 0.68, 0.0, 0.75)
    cl = g.math('MULTIPLY', cl, g.remap(z, 0.03, 0.2, 0.0, 1.0))
    up = g.mix(cl, up, (*srgb(clouds), 1.0))
    col = g.mix(g.remap(z, -soft, 0.0, 0.0, 1.0), (*srgb(below), 1.0), up)
    seen = g.new("ShaderNodeBackground", {"Color": col, "Strength": 1.0})
    lit = g.new("ShaderNodeBackground", {"Color": (*srgb(fill), 1.0), "Strength": fill_strength})
    cam = g.new("ShaderNodeLightPath").outputs["Is Camera Ray"]
    sh = g.new("ShaderNodeMixShader", [cam, lit.outputs[0], seen.outputs[0]])
    nt.links.new(sh.outputs[0], out.inputs["Surface"])
    return w


def finish(scene, *, brush=2, uniformity=4, sharpness=1.0, eccentricity=1.0, haze=None,
           mist=(10.0, 120.0), haze_amount=0.6, bloom=0.0):
    """The whole frame: haze with distance (haze: its colour, or None), the brush filter (brush:
    the Kuwahara filter's size in pixels at 1280 wide, scaled with the resolution; kept small, as
    a bigger one smooths everything into the soft, glossy look of your note of 2026-10-15), and
    bloom (none by default: the look is matte)."""
    r = scene.render
    size = max(2, round(brush * r.resolution_x * r.resolution_percentage / 100 / 1280))
    vl = scene.view_layers[0]
    ng = bpy.data.node_groups.new("Painted finish", 'CompositorNodeTree')
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    g = Nodes(ng)
    if haze is not None:
        vl.use_pass_mist = True                   # before the render layers node, which then offers it
    rl = g.new("CompositorNodeRLayers")
    img = rl.outputs["Image"]
    if haze is not None:
        ms = scene.world.mist_settings
        ms.start, ms.depth, ms.falloff = mist[0], mist[1], 'QUADRATIC'
        f = g.math('MULTIPLY', rl.outputs["Mist"], haze_amount)
        img = g.mix(f, img, (*srgb(haze), 1.0))
    k = g.new("CompositorNodeKuwahara", {"Image": img, "Size": size, "Uniformity": uniformity,
                                         "Sharpness": sharpness, "Eccentricity": eccentricity})
    try:
        k.inputs["Type"].default_value = 'Anisotropic'
    except (TypeError, ValueError):
        pass
    img = k.outputs[0]
    if bloom:
        gl = g.new("CompositorNodeGlare", {"Image": img, "Threshold": 0.85, "Strength": bloom})
        try:
            gl.inputs["Type"].default_value = 'Bloom'
        except (TypeError, ValueError):
            pass
        img = gl.outputs["Image"]
    go = g.new("NodeGroupOutput")
    ng.links.new(img, go.inputs[0])
    scene.compositing_node_group = ng
    r.use_compositing = True
    return ng


def final_look(scene, f0, f1, *, glow=0.25, shadows=(0.86, 0.97, 1.0), highlights=(1.04, 1.0, 0.95),
               vignette=0.3, dispersion=0.006, grain=0.05, contrast=0.0, brush=0, glow_threshold=0.75, sharpen=0.0):
    """The whole frame finished as a film's would be: a soft glow off the lights; a grade, the
    shadows a little teal and the lights a little warm, and contrast; a vignette; a touch of the
    lens's colour fringing at the edges; a fine film grain, new every frame. brush: a light brush
    filter first (Kuwahara, its size in pixels at 1280 wide), turning hard edges into painted ones."""
    ng = bpy.data.node_groups.new("Final look", 'CompositorNodeTree')
    ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    g = Nodes(ng)
    img = g.new("CompositorNodeRLayers").outputs["Image"]
    if brush:
        size = max(2, round(brush * scene.render.resolution_x * scene.render.resolution_percentage / 100 / 1280))
        k = g.new("CompositorNodeKuwahara", {"Image": img, "Size": size, "Uniformity": 4, "Sharpness": 1.0, "Eccentricity": 1.0})
        try:
            k.inputs["Type"].default_value = 'Anisotropic'
        except (TypeError, ValueError):
            pass
        img = k.outputs[0]
    gl = g.new("CompositorNodeGlare", {"Image": img, "Threshold": glow_threshold, "Strength": glow})
    try:
        gl.inputs["Type"].default_value = 'Fog Glow'
    except (TypeError, ValueError):
        pass
    img = gl.outputs["Image"]
    try:
        lum = g.new("CompositorNodeRGBToBW", [img]).outputs[0]
    except RuntimeError:
        sep = g.new("CompositorNodeSeparateColor", [img])
        lum = g.math('MULTIPLY_ADD', sep.outputs[0], 0.3, g.math('MULTIPLY_ADD', sep.outputs[1], 0.59, g.math('MULTIPLY', sep.outputs[2], 0.11)))
    img = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, lum), 0.6), img, g.scale(img, shadows))
    img = g.mix(g.math('MULTIPLY', lum, 0.6), img, g.scale(img, highlights))
    if contrast:
        img = g.new("CompositorNodeBrightContrast", {"Image": img, "Contrast": contrast}).outputs[0]
    if sharpen:                                     # a light sharpen, as a film's frame is crisp
        sh = g.new("CompositorNodeFilter", {"Image": img, "Factor": sharpen})
        for name in ('Sharpen Diamond', 'Sharpen'):
            try:
                sh.inputs["Type"].default_value = name
                break
            except (TypeError, ValueError):
                pass
        img = sh.outputs[0]
    el = g.new("CompositorNodeEllipseMask", {"Size": (0.95, 0.9), "Value": 1.0})
    soft = g.new("CompositorNodeBlur", {"Image": el.outputs[0], "Size": (300, 300)})
    img = g.scale(img, g.remap(soft.outputs[0], 0.0, 1.0, 1.0 - vignette, 1.0, smooth=False))
    ld = g.new("CompositorNodeLensdist", {"Image": img, "Distortion": 0.0, "Dispersion": dispersion})
    img = ld.outputs[0]
    nz = g.new("ShaderNodeTexNoise", {"Scale": 900.0, "Detail": 0.0, "Roughness": 0.5})
    try:
        nz.noise_dimensions = '4D'
        for f, w in ((f0, 0.0), (f1, (f1 - f0) * 3.7)):
            nz.inputs["W"].default_value = w
            nz.inputs["W"].keyframe_insert("default_value", frame=f)
    except Exception:
        pass
    img = g.mix(grain, img, nz.outputs["Fac"], "OVERLAY")
    go = g.new("NodeGroupOutput")
    ng.links.new(img, go.inputs[0])
    scene.compositing_node_group = ng
    scene.render.use_compositing = True
    scene.render.compositor_device = 'GPU'          # the same frame, 2.6 s instead of 6.5 at 1080p
    return ng


def eevee(scene, samples=48):
    """EEVEE for the painted look: soft shadows, AO for the paint's own occlusion, the view
    transform left Standard, so the colours are the ones painted."""
    scene.render.engine = 'BLENDER_EEVEE'
    e = scene.eevee
    e.taa_render_samples = samples
    e.use_shadows = True
    e.use_raytracing = False
    e.use_fast_gi = True
    e.fast_gi_distance = 0.6
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
