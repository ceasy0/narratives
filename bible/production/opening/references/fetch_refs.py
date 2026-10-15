"""Fetch the open-licence reference images for the Opening look book.

The cloud session that wrote REFERENCES.md (one folder up) could not reach any image host
(its egress policy blocked them), so this script does the download on a machine
that can. Run it from this folder:  py fetch_refs.py  (production/opening/references/)
Needs Pillow. Each image is saved to img/ as JPEG quality 85, at most 1600 px on
the long side. Licences and credits are listed below and in REFERENCES.md (one folder up).
"""
import io
import pathlib
import time
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
    # Historical pictures of the beginning (catalogue: ../DEPICTIONS.md)
    ("01-fludd-darkness-1617-wellcome.jpg",
     "https://upload.wikimedia.org/wikipedia/commons/0/01/Darkness%2C_%22De_metaphysico_macrosmi...ortu%22%2C_Fludd%2C_1617_Wellcome_L0016156.jpg",
     "Robert Fludd, Utriusque Cosmi (Oppenheim, 1617); Wellcome Collection, L0016156", "CC BY 4.0",
     "https://commons.wikimedia.org/wiki/File:Darkness,_%22De_metaphysico_macrosmi...ortu%22,_Fludd,_1617_Wellcome_L0016156.jpg"),
    ("01-nash-face-of-the-waters-wellcome.jpg",
     "https://upload.wikimedia.org/wikipedia/commons/f/fc/The_face_of_the_Waters._Wellcome_M0005778.jpg",
     "Paul Nash, Genesis (Nonesuch Press, 1924); Wellcome Collection, M0005778", "CC BY 4.0",
     "https://commons.wikimedia.org/wiki/File:The_face_of_the_Waters._Wellcome_M0005778.jpg"),
    ("01-aivazovsky-chaos-1841.jpg",
     "https://upload.wikimedia.org/wikipedia/commons/6/63/Aivazovsky_Chaos_1841.jpg",
     "Ivan Aivazovsky, Chaos. The Creation of the World, 1841; San Lazzaro degli Armeni, Venice", "Public domain (PD-Art)",
     "https://commons.wikimedia.org/wiki/File:Aivazovsky_Chaos_1841.jpg"),
    ("02-fludd-first-light-1617-wellcome.jpg",
     "https://upload.wikimedia.org/wikipedia/commons/b/bb/%22De_metaphysico_macrosmi...ortu%22%2C_Fludd%2C_1617_Wellcome_L0016162.jpg",
     "Robert Fludd, Utriusque Cosmi (Oppenheim, 1617); Wellcome Collection, L0016162", "CC BY 4.0",
     "https://commons.wikimedia.org/wiki/File:%22De_metaphysico_macrosmi...ortu%22,_Fludd,_1617_Wellcome_L0016162.jpg"),
    ("02-nash-light-from-darkness-wellcome.jpg",
     "https://upload.wikimedia.org/wikipedia/commons/6/6d/The_separation_of_Light_from_Darkness._Wellcome_M0005781.jpg",
     "Paul Nash, Genesis (Nonesuch Press, 1924); Wellcome Collection, M0005781", "CC BY 4.0",
     "https://commons.wikimedia.org/wiki/File:The_separation_of_Light_from_Darkness._Wellcome_M0005781.jpg"),
    ("02-muller-first-day-1589-met.jpg",
     "https://images.metmuseum.org/CRDImages/dp/original/DP261963.jpg",
     "Jan Muller after Hendrick Goltzius, The First Day, 1589; The Metropolitan Museum of Art", "CC0 (Met Open Access)",
     "https://www.metmuseum.org/art/collection/search/374000"),
    ("03-michelangelo-light-from-darkness.jpg",
     "https://upload.wikimedia.org/wikipedia/commons/b/b8/Michelangelo%2C_Separation_of_Light_from_Darkness_00.jpg",
     "Michelangelo, The Separation of Light from Darkness, 1511-12; Sistine Chapel (photograph via Web Gallery of Art)", "Public domain (PD-Art)",
     "https://commons.wikimedia.org/wiki/File:Michelangelo,_Separation_of_Light_from_Darkness_00.jpg"),
    ("05-giovanni-di-paolo-creation-met.jpg",
     "https://images.metmuseum.org/CRDImages/rl/original/DP-40104-001.jpg",
     "Giovanni di Paolo, The Creation of the World and the Expulsion from Paradise, 1445; The Metropolitan Museum of Art", "CC0 (Met Open Access)",
     "https://www.metmuseum.org/art/collection/search/458971"),
    ("05-nash-firmament-wellcome.jpg",
     "https://upload.wikimedia.org/wikipedia/commons/6/64/The_creation_of_the_Firmament._Wellcome_M0005782.jpg",
     "Paul Nash, Genesis (Nonesuch Press, 1924); Wellcome Collection, M0005782", "CC BY 4.0",
     "https://commons.wikimedia.org/wiki/File:The_creation_of_the_Firmament._Wellcome_M0005782.jpg"),
    ("07-bosch-third-day-grisaille.jpg",
     "https://upload.wikimedia.org/wikipedia/commons/a/af/Hieronymus_Bosch_-_Triptych_of_Garden_of_Earthly_Delights_%28outer_wings%29_-_WGA2506.jpg",
     "Hieronymus Bosch, The Garden of Earthly Delights, outer wings, c. 1490-1510; Museo del Prado (photograph via Web Gallery of Art)", "Public domain (PD-Art)",
     "https://commons.wikimedia.org/wiki/File:Hieronymus_Bosch_-_Triptych_of_Garden_of_Earthly_Delights_(outer_wings)_-_WGA2506.jpg"),
    ("12-scheuchzer-homo-ex-humo-wellcome.jpg",
     "https://iiif.wellcomecollection.org/image/V0034174/full/!1600,1600/0/default.jpg",
     "J. J. Scheuchzer, Physica Sacra (1731), Homo ex humo, etching by J. A. Fridrich; Wellcome Collection, V0034174", "Public Domain Mark",
     "https://wellcomecollection.org/works/twbrjsc2"),
]


def fetch(url):
    # Wikimedia rate-limits anonymous agents; its policy asks for a name and a contact.
    req = urllib.request.Request(url, headers={
        "User-Agent": "lookbook-fetch/1.1 (Adonai look book; noreply@anthropic.com)"})
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
            time.sleep(2)  # be gentle with the image hosts
            im = Image.open(io.BytesIO(fetch(url))).convert("RGB")
            im.thumbnail((LONG_SIDE, LONG_SIDE), Image.LANCZOS)
            im.save(dest, "JPEG", quality=85)
            print("saved ", name, im.size, "|", licence, "|", credit)
        except Exception as e:  # report and keep going
            print("FAILED", name, "->", e, "| source page:", page)


if __name__ == "__main__":
    main()
