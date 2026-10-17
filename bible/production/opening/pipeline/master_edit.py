"""Build the Opening's master edit: work/edit/opening-master.blend.

    blender -b --factory-startup -P master_edit.py

One strip per shot of shots.csv, each cut from the v3.1 animatic where that shot
is in it (channel 1; the animatic is 5:00 and the Opening 6:15 since beats 12 and 13 grew,
so opening.animatic_frame maps one to the other; the walk down the Nile, 04:51-05:51, isn't in
the animatic, and its shots are black), the animatic's guide sound under it in three pieces,
shifted the same way (channel 5), and on
channel 2 every layout playblast found in work/playblast/ named
<first shot>-<last shot>-layout.mp4, placed at its first shot's timecode.
A marker stands at the start of each beat. Rebuilding replaces the file.
"""
import sys
import pathlib

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import opening as O  # noqa: E402

W, H = 960, 540

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.data.scenes.new("Opening master edit")
bpy.context.window.scene = scene
for s in list(bpy.data.scenes):
    if s is not scene:
        bpy.data.scenes.remove(s)

r = scene.render
r.fps = O.FPS
r.resolution_x, r.resolution_y, r.resolution_percentage = W, H, 100
scene.frame_start, scene.frame_end = 0, O.TOTAL - 1
scene.frame_set(0)

se = scene.sequence_editor_create()
se.proxy_storage = 'PROJECT'
se.proxy_dir = str(O.LOCAL / "cache" / "master-proxies")

shots = O.shots()
tags = ['COLOR_01', 'COLOR_02', 'COLOR_03', 'COLOR_04', 'COLOR_05', 'COLOR_06', 'COLOR_07']
beat_seen = set()
for sh in shots:
    a, dur = O.animatic_frame(sh["start"]), sh["end"] - sh["start"]
    if a is None:                                # the walk down the Nile: nothing in the animatic
        st = se.strips.new_effect("SH%s %s" % (sh["shot"], sh["what"][:60]), 'COLOR', channel=1,
                                  frame_start=sh["start"], length=dur)
        st.color = (0.0, 0.0, 0.0)
    else:
        st = se.strips.new_movie("SH%s %s" % (sh["shot"], sh["what"][:60]), str(O.ANIMATIC),
                                 channel=1, frame_start=sh["start"] - a, fit_method='FIT')
        st.frame_offset_start = a
        st.frame_offset_end = O.ANIMATIC_TOTAL - a - dur
    st.color_tag = tags[sh["beat"] % len(tags)]
    assert st.frame_final_start == sh["start"] and st.frame_final_end == sh["end"], sh["shot"]
    if sh["beat"] not in beat_seen:
        beat_seen.add(sh["beat"])
        scene.timeline_markers.new("BEAT %d" % sh["beat"], frame=sh["start"])

cut, cut2 = O.frame("04:00"), O.frame("04:36")   # the guide sound: as it is up to 04:00; its 04:00-04:36 (the run and the walk) 15 s later; its beat 14 under ours
snd = se.strips.new_sound("Guide sound (animatic v3.1), to 04:00", str(O.ANIMATIC), channel=5, frame_start=0)
snd.frame_offset_end = O.ANIMATIC_TOTAL - cut
snd = se.strips.new_sound("Guide sound (animatic v3.1), its 04:00-04:36", str(O.ANIMATIC), channel=5,
                          frame_start=O.EXTRA[0] - cut2)
snd.frame_offset_start = cut
snd.frame_offset_end = O.ANIMATIC_TOTAL - cut2
snd = se.strips.new_sound("Guide sound (animatic v3.1), from its 04:36", str(O.ANIMATIC), channel=5,
                          frame_start=O.TOTAL - O.ANIMATIC_TOTAL)
snd.frame_offset_start = cut2

by_id = {sh["shot"]: sh for sh in shots}
for f in sorted(O.PLAYBLAST.glob("*-layout.mp4")):
    first = f.name.split("-")[0]
    if first not in by_id:
        print("skipped (no such shot):", f.name)
        continue
    st = se.strips.new_movie("LAYOUT " + f.stem, str(f), channel=2,
                             frame_start=by_id[first]["start"], fit_method='FIT')
    st.color_tag = 'COLOR_09'
    print("layout strip:", f.name, O.timecode(st.frame_final_start), "to", O.timecode(st.frame_final_end))

r.image_settings.media_type = 'VIDEO'
r.image_settings.file_format = 'FFMPEG'
r.ffmpeg.format = 'MPEG4'
r.ffmpeg.codec = 'H264'
r.ffmpeg.constant_rate_factor = 'MEDIUM'
r.ffmpeg.audio_codec = 'AAC'
r.filepath = str(O.EDIT / "opening-master-preview.mp4")

O.EDIT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O.MASTER))
print("saved", O.MASTER, "|", len(shots), "shot strips")
