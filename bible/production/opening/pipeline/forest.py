"""The forest of the run (beat 13), as real as we can make it, from scanned CC0 assets.

Imported by band_mocap_test.py (its `real` mode) inside Blender 5.0. The fetching half runs
outside Blender too, to download everything once:

    py forest.py            fetch every asset below into ASSETS (about 1.3 GB, once)

Poly Haven (polyhaven.com) publishes its models and textures as CC0: no conditions, no credit
needed. Its API (api.polyhaven.com) is free for any use; its terms ask only that requests name
the software making them (UA below). Files land in ASSETS, out of git.

What `dress` builds, around the layout's travelling camera and the band's lane:
- the tall trees, at the layout's own places and heights: trunks made here (tapering, leaning a
  little, buttressed at the foot) in scanned bark, with limbs carrying crowns of real branches
  and leaves (Poly Haven's small tree, its trunk taken off), and more crowns overhead where the
  layout leaves the camera's side of the lane bare, so the sun comes through in patches;
- the understory, layered by distance: saplings, shrubs, ferns, tropical plants, roots, logs,
  stumps, rocks and fallen branches, kept off the runners' lane and thin between it and the camera;
- the floor: four scanned grounds (leaf litter, mud, and a bare trail along the lane), mixed by
  noise and displaced for real by their height maps, finer near the camera (adaptive subdivision);
- the light: a sky, a sun from the band's left, and haze in the air for the shafts.
"""
import json
import math
import pathlib
import random
import re
import urllib.request

try:
    import bpy
    import bmesh
    import numpy as np
    from mathutils import Matrix, Vector
except ImportError:                           # the fetching half, outside Blender
    bpy = None

API = "https://api.polyhaven.com"
UA = "AdonaiOpening-pipeline/1.0 (Blender scripts for a film)"
ASSETS = pathlib.Path(r"C:\Users\corbi\AdonaiOpening\assets\polyhaven")

# What the forest is made of. Models, by what they're for.
CROWNS = ["tree_small_02", "island_tree_01"]                  # branches and leaves, high on the tall trunks
UNDERSTORY = ["tree_small_02", "island_tree_02", "island_tree_03"]
PLANTS = ["fern_02", "shrub_01", "shrub_02", "shrub_03", "shrub_04", "nettle_plant", "weed_plant_02",
          "pachira_aquatica_01", "calathea_orbifolia_01", "anthurium_botany_01"]
FLOOR = ["root_cluster_01", "root_cluster_02", "single_root", "dead_tree_trunk", "dead_tree_trunk_02",
         "tree_stump_01", "tree_stump_02", "rock_07", "rock_09", "boulder_01", "moss_01",
         "dry_branches_medium_01"]
GRASS = ["grass_medium_01"]
MODELS = sorted(set(CROWNS + UNDERSTORY + PLANTS + FLOOR + GRASS))
# Textures: the forest floor, the trail the band runs on, bark, and leather for the hides.
GROUND = ["forest_leaves_02", "leaves_forest_ground", "brown_mud_leaves_01"]
TRAIL = ["dirt_floor"]
BARK = ["jolcham_oak_bark_01", "bark_brown_02", "chinese_hackberry_bark", "eucalyptus_bark"]
HIDE = ["fabric_leather_02", "brown_leather"]
TEXTURES = GROUND + TRAIL + BARK + HIDE
MAPS = {"Diffuse": "jpg", "nor_gl": "jpg", "Rough": "jpg", "Displacement": "png"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def download(url, path):
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(get(url))
    tmp.replace(path)
    return path


def files(asset):
    return json.loads(get("%s/files/%s" % (API, asset)))


def model(asset, res="2k"):
    """A Poly Haven model's .blend and its textures, fetched once; returns the .blend's path."""
    here = ASSETS / "models" / asset
    blend = here / ("%s_%s.blend" % (asset, res))
    if blend.exists():
        return blend
    entry = files(asset)["blend"][res]["blend"]
    for rel, inc in entry.get("include", {}).items():
        download(inc["url"], here / rel)
    return download(entry["url"], blend)


def texture(asset, res=None):
    """A Poly Haven texture's maps (colour, normal, roughness, height), fetched once."""
    res = res or ("4k" if asset in GROUND + TRAIL else "2k")
    here = ASSETS / "textures" / asset
    out = {}
    listing = None
    for kind, fmt in MAPS.items():
        path = here / ("%s_%s_%s.%s" % (asset, kind.lower(), res, fmt))
        if not path.exists():
            listing = listing or files(asset)
            if kind not in listing:
                continue
            download(listing[kind][res][fmt]["url"], path)
        out[kind] = path
    return out


def size(asset):
    """How wide a texture is in the world, metres (Poly Haven measures each scan), fetched once."""
    path = ASSETS / "textures" / asset / "info.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(get("%s/info/%s" % (API, asset)))
    w, h = json.loads(path.read_text())["dimensions"][:2]
    return w / 1000.0, h / 1000.0


# ---------------------------------------------------------------- inside Blender: assets
_PARTS = {}


def parts(asset, lod=0, only=None, keep=None):
    """A Poly Haven model's meshes, one per part, at the level of detail asked (or the nearest
    finer one). only: a pattern the part's name must match; keep: words, one of which a
    material's name must contain for its faces to stay (the rest are cut away)."""
    key = (asset, lod, only, tuple(keep or ()))
    if key in _PARTS:
        return _PARTS[key]
    with bpy.data.libraries.load(str(model(asset)), link=False) as (src, dst):
        dst.objects = list(src.objects)
    groups = {}
    for o in dst.objects:
        if o is not None and o.type == 'MESH':
            m = re.match(r"(.*)_LOD(\d)$", o.name)
            base, level = (m.group(1), int(m.group(2))) if m else (o.name, 0)
            if only is None or re.search(only, base):
                groups.setdefault(base, {})[level] = o.data
    for o in dst.objects:
        if o is not None:
            bpy.data.objects.remove(o)
    out = []
    for base, lods in sorted(groups.items()):
        have = sorted(lods)
        me = lods[max([x for x in have if x <= lod], default=have[0])]
        if keep:
            names = [m.name.lower() if m else "" for m in me.materials]
            bm = bmesh.new()
            bm.from_mesh(me)
            gone = [f for f in bm.faces if not any(k in names[f.material_index] for k in keep)]
            bmesh.ops.delete(bm, geom=gone, context='FACES')
            me = me.copy()
            bm.to_mesh(me)
            bm.free()
        out.append(me)
    _PARTS[key] = out
    return out


def put(col, me, loc, rot=0.0, s=1.0, name=None, tilt=(0.0, 0.0)):
    ob = bpy.data.objects.new(name or me.name, me)
    ob.location = loc
    ob.rotation_euler = (tilt[0], tilt[1], rot)
    ob.scale = (s, s, s)
    col.objects.link(ob)
    return ob


def islands(ob):
    """The separate pieces of a layout mesh: (centre x, y, lowest z, highest z, radius at its
    foot, number of faces), in world space."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    mw = ob.matrix_world
    seen, out = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        island, todo = [], [f]
        seen.add(f.index)
        while todo:
            g = todo.pop()
            island.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        todo.append(h)
        vs = {v for g in island for v in g.verts}
        co = np.array([tuple(mw @ v.co) for v in vs])
        lo = co[:, 2].min()
        foot = co[co[:, 2] < lo + 0.05]
        c = co[:, :2].mean(0)
        r = float(np.max(np.linalg.norm(foot[:, :2] - foot[:, :2].mean(0), axis=1))) if len(foot) > 2 else 0.3
        out.append((float(c[0]), float(c[1]), float(lo), float(co[:, 2].max()), r, len(island)))
    bm.free()
    return out


# ---------------------------------------------------------------- materials
def mix(nt, fac, a, b, kind):
    """A Mix node of `kind` ('FLOAT', 'RGBA' or 'VECTOR') between sockets a and b by fac."""
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = kind
    want = {'FLOAT': 'VALUE', 'RGBA': 'RGBA', 'VECTOR': 'VECTOR'}[kind]
    ins = [s for s in m.inputs if s.type == want and s.name in ("A", "B")]
    nt.links.new(fac, m.inputs["Factor"] if kind != 'VECTOR' else m.inputs[0])
    nt.links.new(a, ins[0])
    nt.links.new(b, ins[1])
    return [s for s in m.outputs if s.type == want][0]


def layer(nt, coord, asset, turn=0.0):
    """One scanned texture, laid on `coord` (metres) at its real size: colour, roughness, normal
    colour and height sockets."""
    maps = texture(asset)
    w, h = size(asset)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0 / w, 1.0 / h, 1.0)
    mp.inputs["Rotation"].default_value = (0, 0, turn)
    nt.links.new(coord, mp.inputs["Vector"])
    out = {}
    for kind in ("Diffuse", "Rough", "nor_gl", "Displacement"):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = bpy.data.images.load(str(maps[kind]), check_existing=True)
        if kind != "Diffuse":
            t.image.colorspace_settings.name = 'Non-Color'
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        out[kind] = t.outputs["Color"]
    return out


def noise_fac(nt, coord, scale, lo, hi, detail=3.0):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    nt.links.new(coord, n.inputs["Vector"])
    r = nt.nodes.new("ShaderNodeMapRange")
    r.inputs["From Min"].default_value, r.inputs["From Max"].default_value = lo, hi
    nt.links.new(n.outputs["Fac"], r.inputs["Value"])
    return r.outputs["Result"]


def finish(nt, layers_mixed, depth, tint=None):
    """Wire mixed colour, roughness, normal and height into a Principled BSDF and the output's
    displacement (`depth` metres from the darkest to the brightest of the height map)."""
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    col = layers_mixed["Diffuse"]
    if tint is not None:
        t = nt.nodes.new("ShaderNodeMix")
        t.data_type, t.blend_type = 'RGBA', 'MULTIPLY'
        t.inputs[0].default_value = 1.0
        a, b = [s for s in t.inputs if s.type == 'RGBA'][:2]
        nt.links.new(col, a)
        b.default_value = (*tint, 1.0)
        col = [s for s in t.outputs if s.type == 'RGBA'][0]
    nt.links.new(col, p.inputs["Base Color"])
    nt.links.new(layers_mixed["Rough"], p.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(layers_mixed["nor_gl"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    d = nt.nodes.new("ShaderNodeDisplacement")
    d.inputs["Midlevel"].default_value = 0.5
    d.inputs["Scale"].default_value = depth
    nt.links.new(layers_mixed["Displacement"], d.inputs["Height"])
    nt.links.new(d.outputs["Displacement"], out.inputs["Displacement"])
    return p


def new_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    for n in list(m.node_tree.nodes):
        m.node_tree.nodes.remove(n)
    m.displacement_method = 'BOTH'
    return m


def ground_material():
    """Leaf litter, a second litter and mud, mixed in patches tens of metres across; the bare
    trail where the `trail` attribute says (along the band's lane)."""
    m = new_material("Forest floor, scanned")
    nt = m.node_tree
    coord = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    a = layer(nt, coord, "forest_leaves_02")
    b = layer(nt, coord, "leaves_forest_ground", 0.7)
    c = layer(nt, coord, "brown_mud_leaves_01", 1.9)
    t = layer(nt, coord, "dirt_floor", 0.3)
    f_ab = noise_fac(nt, coord, 0.07, 0.42, 0.58)
    f_c = noise_fac(nt, coord, 0.13, 0.58, 0.68)
    trail = nt.nodes.new("ShaderNodeAttribute")
    trail.attribute_name = "trail"
    edge = noise_fac(nt, coord, 2.5, 0.3, 0.7, 4.0)
    tm = nt.nodes.new("ShaderNodeMath")
    tm.operation, tm.use_clamp = 'MULTIPLY_ADD', True
    nt.links.new(trail.outputs["Fac"], tm.inputs[0])
    tm.inputs[1].default_value = 1.6
    tm.inputs[2].default_value = -0.3
    tf = nt.nodes.new("ShaderNodeMath")
    tf.operation, tf.use_clamp = 'MULTIPLY', True
    nt.links.new(tm.outputs[0], tf.inputs[0])
    nt.links.new(edge, tf.inputs[1])
    mixed = {}
    for kind, how in (("Diffuse", 'RGBA'), ("Rough", 'FLOAT'), ("nor_gl", 'RGBA'), ("Displacement", 'FLOAT')):
        s = mix(nt, f_ab, a[kind], b[kind], how)
        s = mix(nt, f_c, s, c[kind], how)
        mixed[kind] = mix(nt, tf.outputs[0], s, t[kind], how)
    finish(nt, mixed, 0.05)
    return m


def bark_material(asset, tint):
    """A scanned bark, mapped in metres on the trunk's UVs, displaced for real."""
    m = new_material("Bark, " + asset)
    nt = m.node_tree
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    finish(nt, layer(nt, uv.outputs["UV"], asset), 0.025, tint)
    return m


def adaptive(ob, pixels=1.5):
    """Cycles dices the mesh finer near the camera, so its material's height becomes real relief."""
    s = ob.modifiers.new("Relief", 'SUBSURF')
    s.subdivision_type = 'SIMPLE'
    s.levels = 0
    s.use_adaptive_subdivision = True
    s.adaptive_pixel_size = pixels


# ---------------------------------------------------------------- the tall trees
def trunk(h, r, seed):
    """A tall forest trunk h m high, r m in radius at the foot (above the buttresses): it tapers,
    leans and wavers a little, and spreads into 3 to 6 buttress fins at the ground. Returns the
    mesh (UVs in metres) and where its limbs end (for crowns), in its own space."""
    rng = random.Random(seed)
    seg = 40
    lobes, fin = rng.randint(3, 6), rng.uniform(0.8, 1.8)
    lean = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized() * rng.uniform(0.2, 0.6)
    ph = [rng.uniform(0, 2 * math.pi) for _ in range(4)]
    zs = [0.0] + [h * (k / 60.0) ** 1.4 for k in range(1, 61)]
    bm = bmesh.new()
    uvs, rings = [], []
    for z in zs:
        u = z / h
        axis = lean * u * u + Vector((0.12 * math.sin(3 * u + ph[0]), 0.12 * math.sin(2.3 * u + ph[1]), 0))
        rad = r * (1 - 0.55 * u) * (1 + 0.5 * math.exp(-z / 0.35))
        ring = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            fins = fin * max(0.0, math.cos(lobes * (a + ph[2]) / 2)) ** 6 * math.exp(-z / 0.9)
            wob = 1 + 0.04 * math.sin(5 * a + 7 * u + ph[3]) + 0.025 * math.sin(11 * a)
            rr = rad * wob + r * fins
            ring.append(bm.verts.new((axis.x + rr * math.cos(a), axis.y + rr * math.sin(a), z - 0.15 * math.exp(-z / 0.2) * fins)))
        rings.append(ring)
    uv_rows = []
    for k, ring in enumerate(rings):
        uv_rows.append([(2 * math.pi * r * j / seg, zs[k]) for j in range(seg + 1)])
    faces = []
    for k in range(len(rings) - 1):
        for j in range(seg):
            f = bm.faces.new((rings[k][j], rings[k][(j + 1) % seg], rings[k + 1][(j + 1) % seg], rings[k + 1][j]))
            faces.append((f, ((k, j), (k, j + 1), (k + 1, j + 1), (k + 1, j))))
    top = bm.faces.new(list(reversed(rings[-1])))
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for f, idx in faces:
        for loop, (k, j) in zip(f.loops, idx):
            loop[uv_layer].uv = uv_rows[k][j]
    for loop in top.loops:
        loop[uv_layer].uv = (0.0, h)
    # Limbs: up and out from the upper trunk, tapering; their ends carry the crowns.
    tips = []
    for i in range(rng.randint(4, 6)):
        z0 = h * rng.uniform(0.72, 0.9)
        u = z0 / h
        base = lean * u * u
        ang = 2 * math.pi * i / 6 + rng.uniform(-0.4, 0.4)
        length = h * rng.uniform(0.12, 0.22)
        d = Vector((math.cos(ang), math.sin(ang), rng.uniform(0.7, 1.3))).normalized()
        rad0 = r * (1 - 0.55 * u) * 0.45
        m = Matrix.Translation(Vector((base.x, base.y, z0)) + d * length / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        made = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=rad0, radius2=rad0 * 0.35, depth=length, matrix=m)
        for f in {f for v in made["verts"] for f in v.link_faces}:
            for loop in f.loops:
                p = m.inverted() @ loop.vert.co
                loop[uv_layer].uv = (math.atan2(p.y, p.x) * rad0, p.z)
        tips.append(Vector((base.x, base.y, z0)) + d * length)
    tips.append(Vector((lean.x, lean.y, h)))
    me = bpy.data.meshes.new("Trunk")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me, tips


# ---------------------------------------------------------------- dressing the shot
def dress(scene, cam, lane_x, frames, seed=1):
    """Swap the layout's grey forest for the scanned one, around the camera's path between
    frames[0] and frames[1], and light it. Leaves the people and the cat alone."""
    rng = random.Random(seed)
    col = bpy.data.collections.new("Forest, scanned")
    scene.collection.children.link(col)
    cams = []
    for f in frames:
        scene.frame_set(f)
        cams.append(cam.matrix_world.translation.copy())
    CX = cams[0].x
    Y0, Y1 = min(c.y for c in cams), max(c.y for c in cams)
    YM = (Y0 + Y1) / 2

    def seen(x, y, margin=6.0):
        """In or near the camera's view over the shot (it looks along +X)."""
        dx = x - CX
        return dx > 0.3 and abs(y - YM) < 0.6 * dx + (Y1 - Y0) / 2 + margin

    lane = (lane_x - 1.8, lane_x + 2.1)

    # The layout's trees, read before they go: forest trees, the woodland's, the wipe trunks.
    scene.frame_set(frames[0])
    tall = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.hide_render:
            continue
        if re.match(r"Tree(\.\d+)?$", ob.name) or ob.name.startswith("Tree, west"):
            pieces = islands(ob)                              # a trunk (cone) and a crown (ball)
            foot = min(pieces, key=lambda p: p[2])
            top = max(p[3] for p in pieces)
            if top > 2:
                tall.append((foot[0], foot[1], top, max(foot[4], 0.22), False))
        elif ob.name.startswith("Trees beyond the forest"):
            for x, y, lo, hi, r, n in islands(ob):
                if n <= 14:                                   # trunks, not crowns: the open woodland's, 8-14 m
                    tall.append((x, y, rng.uniform(8, 14), max(r, 0.2), False))
        elif ob.name.startswith("Trunk"):                    # the trunk that wipes across the lens
            for x, y, lo, hi, r, n in islands(ob):
                tall.append((x, y, hi, r, True))
    for ob in bpy.data.objects:                              # the grey world goes; people, cat, camera stay
        if ob.type == 'MESH' and not ob.name.startswith("Mocap ") and ob.name != "Big cat":
            ob.hide_render = True
    tall = [t for t in tall if seen(t[0], t[1], 25.0) or t[4]]
    print("tall trees", len(tall))

    # Trunks and crowns.
    barks = [bark_material(a, tint) for a, tint in zip(BARK, ((1, 1, 1), (0.85, 0.82, 0.8), (0.9, 0.88, 0.85), (0.75, 0.72, 0.7)))]
    crowns = parts("tree_small_02", 1, only=r"^tree_small_02$", keep=("branches", "leaves")) + \
        parts("island_tree_01", 1, only=r"^island_tree_01$", keep=("branches", "leaves"))
    roots = parts("root_cluster_01")
    for i, (x, y, h, r, wipe) in enumerate(tall):
        me, tips = trunk(h, r, seed * 1000 + i)
        me.materials.append(barks[i % len(barks)])
        ob = put(col, me, (x, y, 0.0), rng.uniform(0, 2 * math.pi), name="Tall tree")
        if x - CX < 14 or wipe:                           # bark in relief only where it can be seen
            adaptive(ob, 2.0)
        if wipe:
            continue
        for tip in tips:                                  # the crown hangs round the limbs' ends, and below
            w = ob.matrix_basis @ tip                     # (matrix_world isn't set until the scene updates)
            c = crowns[0] if rng.random() < 0.7 else crowns[1]
            s = rng.uniform(1.5, 2.4) if c is crowns[0] else rng.uniform(0.9, 1.3)
            put(col, c, (w.x, w.y, w.z - 2.6 * s), rng.uniform(0, 2 * math.pi), s, name="Crown")
        if r > 0.3 and rng.random() < 0.35:
            put(col, roots[0], (x, y, -0.05), rng.uniform(0, 2 * math.pi), r * 1.6, name="Roots")

    # Crowns over the strip between the camera and the lane, where the layout has no trees: out
    # of frame overhead, they put the band in broken light, as under a forest's canopy.
    for _ in range(70):
        x, y = rng.uniform(CX - 6, lane[1] + 3), rng.uniform(Y0 - 30, Y1 + 30)
        c = crowns[0] if rng.random() < 0.7 else crowns[1]
        s = rng.uniform(1.6, 2.4) if c is crowns[0] else rng.uniform(1.0, 1.3)
        put(col, c, (x, y, rng.uniform(13, 18)), rng.uniform(0, 2 * math.pi), s, name="Crown overhead")

    def clear(x, y, gap):
        return all((x - t[0]) ** 2 + (y - t[1]) ** 2 > (t[3] + gap) ** 2 for t in tall)

    def scatter(meshes, n, near, far, size, gap=0.3, lane_ok=False, near_ok=True, woods=1.0, name="Plant", tilt=0.0):
        """n of `meshes` between `near` and `far` m from the camera, sized by `size` (lo, hi)."""
        placed = 0
        if not meshes:
            return 0
        for _ in range(n * 30):
            x = CX + near + (far - near) * rng.random() ** 1.3
            y = rng.uniform(Y0 - 0.6 * (x - CX) - 8, Y1 + 0.6 * (x - CX) + 8)
            if not seen(x, y) or not clear(x, y, gap):
                continue
            if lane[0] < x < lane[1] and not lane_ok:
                continue
            if x < lane[0] and not near_ok:
                continue
            if y > 47 and rng.random() > woods:                 # the open woodland: fewer
                continue
            s = rng.uniform(*size)
            if x < lane[0]:
                s *= 0.7
            put(col, rng.choice(meshes), (x, y, -0.01), rng.uniform(0, 2 * math.pi), s, name=name,
                tilt=(rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt)))
            placed += 1
            if placed >= n:
                break
        return placed

    counts = {}
    counts["saplings"] = scatter(parts("tree_small_02", 1, only=r"^tree_small_02$"), 70, 6, 70, (0.7, 1.5), 0.8, near_ok=False, woods=0.6, name="Sapling")
    counts["small trees"] = scatter(parts("island_tree_02", 1, only=r"^island_tree_0\d$") + parts("island_tree_03", 1, only=r"^island_tree_0\d$"),
                                    10, 20, 80, (0.8, 1.1), 2.0, near_ok=False, name="Small tree")
    counts["shrubs"] = scatter(parts("shrub_02", 0) + parts("pachira_aquatica_01", 0, keep=("leaves", "bark")), 260, 4, 70, (0.8, 1.5), 0.4, near_ok=False, name="Shrub")
    counts["tropical"] = scatter(parts("anthurium_botany_01") + parts("calathea_orbifolia_01"), 260, 2, 40, (1.0, 1.8), 0.2, name="Plant")
    counts["ferns"] = scatter(parts("fern_02"), 700, 1.5, 60, (0.8, 1.6), 0.2, woods=0.5, name="Fern")
    counts["small plants"] = scatter(parts("shrub_01", 1) + parts("shrub_03", 1) + parts("shrub_04", 1) + parts("nettle_plant", 1) + parts("weed_plant_02", 1),
                                     1400, 1, 35, (1.0, 2.2), 0.1, name="Small plant")
    counts["logs"] = scatter(parts("dead_tree_trunk") + parts("dead_tree_trunk_02", 1), 26, 3, 60, (0.8, 1.3), 0.6, near_ok=True, name="Log")
    counts["stumps"] = scatter(parts("tree_stump_01") + parts("tree_stump_02"), 10, 4, 60, (0.7, 1.1), 0.6, name="Stump")
    counts["roots"] = scatter(parts("single_root", 1) + parts("root_cluster_02"), 60, 2, 50, (0.8, 1.4), 0.1, name="Root")
    counts["rocks"] = scatter(parts("rock_07", 1) + parts("rock_09", 1), 110, 1, 60, (0.8, 2.5), 0.2, name="Rock")
    counts["boulders"] = scatter(parts("boulder_01", 2), 8, 8, 60, (0.25, 0.55), 0.5, near_ok=False, name="Boulder")
    counts["branches"] = scatter(parts("dry_branches_medium_01"), 160, 0.8, 30, (0.8, 1.5), 0.05, lane_ok=True, name="Fallen branch", tilt=0.05)
    print("scattered", counts)

    # The floor: a 1 m grid over everything the camera sees, its trail along the lane.
    x0, x1, y0, y1 = CX - 8, CX + 220, Y0 - 160, Y1 + 160
    nx, ny = int(x1 - x0) + 1, int(y1 - y0) + 1
    gx, gy = np.meshgrid(np.linspace(x0, x1, nx), np.linspace(y0, y1, ny), indexing="xy")
    verts = np.stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)], 1)
    idx = np.arange(nx * ny).reshape(ny, nx)
    quads = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    me = bpy.data.meshes.new("Forest floor")
    me.from_pydata(verts.tolist(), [], quads.tolist())
    me.update()
    wav = 0.6 * np.sin(gy.ravel() / 7.0) + 0.3 * np.sin(gy.ravel() / 2.3 + 1.0)
    d = np.abs(gx.ravel() - (lane_x + 0.15) - wav)
    me.attributes.new("trail", 'FLOAT', 'POINT').data.foreach_set("value", np.clip(1.4 - d / 1.1, 0, 1))
    me.materials.append(ground_material())
    floor = bpy.data.objects.new("Forest floor", me)
    col.objects.link(floor)
    adaptive(floor, 1.5)

    # Light: the sky, a sun from high on the band's left and ahead, haze for the shafts.
    world = scene.world
    world.use_nodes = True
    wn = world.node_tree
    for n in list(wn.nodes):
        wn.nodes.remove(n)
    wout = wn.nodes.new("ShaderNodeOutputWorld")
    sky = wn.nodes.new("ShaderNodeTexSky")
    sky.sky_type = 'MULTIPLE_SCATTERING'
    el, az = math.radians(40), math.radians(75)
    sky.sun_elevation, sky.sun_rotation, sky.sun_disc = el, az - math.pi / 2, False
    bg = wn.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 0.35
    wn.links.new(sky.outputs["Color"], bg.inputs["Color"])
    wn.links.new(bg.outputs[0], wout.inputs["Surface"])
    sd = bpy.data.lights.new("Sun", 'SUN')
    sd.energy, sd.angle, sd.color = 4.5, math.radians(0.6), (1.0, 0.93, 0.82)
    sun = bpy.data.objects.new("Sun", sd)
    sun.rotation_euler = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))).to_track_quat('Z', 'Y').to_euler()
    col.objects.link(sun)
    hm = bpy.data.materials.new("Haze")
    hm.use_nodes = True
    ht = hm.node_tree
    for n in list(ht.nodes):
        ht.nodes.remove(n)
    v = ht.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = 0.003
    v.inputs["Anisotropy"].default_value = 0.55
    v.inputs["Color"].default_value = (0.92, 0.94, 1.0, 1)
    ht.links.new(v.outputs[0], ht.nodes.new("ShaderNodeOutputMaterial").inputs["Volume"])
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((CX + 70, YM, 20)) @ Matrix.Diagonal((160, 220, 40, 1)))
    hz = bpy.data.meshes.new("Haze")
    bm.to_mesh(hz)
    bm.free()
    hz.materials.append(hm)
    col.objects.link(bpy.data.objects.new("Haze", hz))
    return {"tall": len(tall), **counts}


if __name__ == "__main__":
    for a in MODELS:
        print("model", a, model(a))
    for a in TEXTURES:
        print("texture", a, sorted(texture(a)), size(a))
