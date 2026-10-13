"""Fetch the open-licence reference images for the Opening look book.

The cloud session that wrote REFERENCES.md (one folder up) could not reach any image host
(its egress policy blocked them), so this script does the download on a machine
that can. Run it from this folder:  py fetch_refs.py  (production/opening/references/)
Needs Pillow. Each image is saved to img/ as JPEG quality 85, at most 1600 px on
the long side. Licences and credits are listed below and in REFERENCES.md (one folder up).
"""
import io
import pathlib
import urllib.request

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "img"
LONG_SIDE = 1600

# (filename, direct URL, credit, licence, source page)
IMAGES = [
    ("01-namib-sand-sea-nasa.jpg",
     "https://assets.science.nasa.gov/content/dam/science/esd/eo/images/imagerecords/149000/149130/namibdunes_hwk_202020_lrg.jpg",
     "NASA Earth Observatory image by Alan Holmes (NASA Ocean Color Web), SeaHawk/HawkEye data", "Public domain (NASA)",
     "https://science.nasa.gov/earth/earth-observatory/namib-sand-sea-149130/"),
    ("02-schlieren-shockwaves-nasa.jpg",
     "https://www.nasa.gov/wp-content/uploads/2023/03/f4_p4_plane_drop_v.jpg",
     "NASA", "Public domain (NASA)",
     "https://www.nasa.gov/image-article/nasa-captures-supersonic-shock-interaction-7"),
    ("04-mud-cracks-mars-pia21261.jpg",
     "https://d2pn8kiwq2w21t.cloudfront.net/original_images/jpegPIA21261.jpg",
     "NASA/JPL-Caltech/MSSS", "Public domain (NASA)",
     "https://www.jpl.nasa.gov/images/pia21261-possible-mud-cracks-preserved-in-martian-rock/"),
    ("04-bentley-snowflake-382.jpg",
     "https://siarchives.si.edu/edan/download/siris_arc_403534",
     "Wilson A. Bentley, c. 1890; Smithsonian Institution Archives", "CC0",
     "https://siarchives.si.edu/collections/siris_arc_403534"),
    ("07-cosmic-web-sim-eso0120a.jpg",
     "https://cdn.eso.org/images/screen/eso0120a.jpg",
     "ESO (simulation by Tom Theuns, MPA Garching)", "CC BY 4.0",
     "https://www.eso.org/public/images/eso0120a/"),
    ("07-cosmic-web-slime-mould-heic2003a.jpg",
     "https://cdn.esahubble.org/archives/images/screen/heic2003a.jpg",
     "NASA, ESA, and J. Burchett and O. Elek (UC Santa Cruz)", "CC BY 4.0",
     "https://esahubble.org/images/heic2003a/"),
    ("08-pillars-of-creation-webb-weic2216a.jpg",
     "https://cdn.esawebb.org/archives/images/wallpaper5/weic2216a.jpg",
     "NASA, ESA, CSA, STScI; J. DePasquale, A. Koekemoer, A. Pagan (STScI)", "CC BY 4.0",
     "https://esawebb.org/images/weic2216a/"),
    ("08-cosmic-cliffs-webb-weic2205a.jpg",
     "https://cdn.esawebb.org/archives/images/screen/weic2205a.jpg",
     "NASA, ESA, CSA, and STScI", "CC BY 4.0",
     "https://esawebb.org/images/weic2205a/"),
    ("08-crab-nebula-webb-weic2326a.jpg",
     "https://cdn.esawebb.org/archives/images/screen/weic2326a.jpg",
     "NASA, ESA, CSA, STScI, T. Temim (Princeton University)", "CC BY 4.0",
     "https://esawebb.org/images/weic2326a/"),
    ("08-sun-granulation-inouye.jpg",
     "https://noirlab.edu/public/media/archives/images/screen/NSO-DKIST-firstlight-full.jpg",
     "NSO/NSF/AURA", "CC BY 4.0",
     "https://noirlab.edu/public/images/NSO-DKIST-firstlight-full/"),
    ("09-sun-loops-sdo-pia22475.jpg",
     "https://assets.science.nasa.gov/content/dam/science/psd/photojournal/pia/pia22/pia22475/PIA22475.jpg",
     "NASA/GSFC/Solar Dynamics Observatory", "Public domain (NASA)",
     "https://science.nasa.gov/photojournal/dynamic-looping-action/"),
    ("09-blue-marble-apollo17.jpg",
     "https://www.nasa.gov/wp-content/uploads/2023/03/as17-148-22727_lrg_0.jpg",
     "NASA (Apollo 17 crew, AS17-148-22727)", "Public domain (NASA)",
     "https://www.nasa.gov/image-article/blue-marble-view-from-apollo-17/"),
    ("09-sunglint-clouds-iss.jpg",
     "https://assets.science.nasa.gov/content/dam/science/esd/eo/images/imagerecords/78000/78107/ISS031-E-035310_lrg.jpg",
     "ISS Crew Earth Observations, NASA JSC (ISS031-E-35310)", "Public domain (NASA)",
     "https://science.nasa.gov/earth/earth-observatory/sunglint-and-clouds-off-western-south-america-78107/"),
    ("11-yucatan-relief-pia03381.jpg",
     "https://d2pn8kiwq2w21t.cloudfront.net/original_images/jpegPIA03381.jpg",
     "NASA/JPL (SRTM)", "Public domain (NASA)",
     "https://www.jpl.nasa.gov/images/pia03381-shaded-relief-with-height-as-color-and-landsat-yucatan-peninsula-mexico"),
    ("14-nile-delta-night-iss.jpg",
     "https://assets.science.nasa.gov/content/dam/science/esd/eo/images/imagerecords/46000/46820/ISS025-E-09858_lrg.jpg",
     "ISS Crew Earth Observations, NASA JSC (ISS025-E-9858)", "Public domain (NASA)",
     "https://science.nasa.gov/earth/earth-observatory/nile-river-delta-at-night-46820/"),
    ("14-okavango-delta-iss.jpg",
     "https://assets.science.nasa.gov/content/dam/science/esd/eo/images/imagerecords/84000/84078/ISS040-E-008209_lrg.jpg",
     "ISS Crew Earth Observations, NASA JSC (ISS040-E-8209)", "Public domain (NASA)",
     "https://science.nasa.gov/earth/earth-observatory/okavango-delta-84078/"),
    ("14-snow-geese-liftoff-usfws.jpg",
     "https://www.fws.gov/sites/default/files/2021-06/Afternoon_Liftoff_of_Snow_Geese_Loess_Bluffs_nwr_Robert_L_Keyser_III.jpg",
     "Robert L. Keyser III / USFWS", "Public domain (USFWS)",
     "https://www.fws.gov/media/afternoon-liftoff-snow-geese-loess-bluffs-national-wildlife-refuge"),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "lookbook-fetch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    OUT.mkdir(exist_ok=True)
    for name, url, credit, licence, page in IMAGES:
        dest = OUT / name
        if dest.exists():
            print("have  ", name)
            continue
        try:
            im = Image.open(io.BytesIO(fetch(url))).convert("RGB")
            im.thumbnail((LONG_SIDE, LONG_SIDE), Image.LANCZOS)
            im.save(dest, "JPEG", quality=85)
            print("saved ", name, im.size, "|", licence, "|", credit)
        except Exception as e:  # report and keep going
            print("FAILED", name, "->", e, "| source page:", page)


if __name__ == "__main__":
    main()
