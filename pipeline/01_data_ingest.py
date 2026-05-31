"""
Module 1 — Data Ingest
======================
Authenticates with Google Earth Engine, submits export tasks for:
  - Sentinel-2 bare-soil composites (two seasonal windows)
  - SRTM terrain stack

Then polls until tasks complete and downloads the GeoTIFFs from Google Drive
into data/raw/.

Usage:
    python pipeline/01_data_ingest.py [--district Krishna] [--skip-gee]
"""

import argparse
import os
import time
from pathlib import Path

import ee
from loguru import logger

from config import (
    BARE_SOIL_WINDOWS,
    BARE_SOIL_NDVI_MAX,
    GEE_DRIVE_FOLDER,
    GEE_PROJECT,
    PILOT_BBOX,
    RAW_DIR,
    TARGET_CRS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def authenticate_gee():
    """Authenticate and initialise Earth Engine."""
    try:
        ee.Initialize(project=GEE_PROJECT)
        logger.info("GEE already authenticated.")
    except Exception:
        logger.info("Running GEE authentication flow…")
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)
        logger.info("GEE authenticated and initialised.")


def get_aoi(district: str | None) -> ee.Geometry:
    """Return EE geometry for the given district or full AP."""
    if district:
        fc = (
            ee.FeatureCollection("FAO/GAUL/2015/level2")
            .filter(ee.Filter.And(
                ee.Filter.eq("ADM1_NAME", "Andhra Pradesh"),
                ee.Filter.eq("ADM2_NAME", district),
            ))
        )
        return fc.geometry()
    # Full AP
    return (
        ee.FeatureCollection("FAO/GAUL/2015/level1")
        .filter(ee.Filter.eq("ADM1_NAME", "Andhra Pradesh"))
        .geometry()
    )


# ---------------------------------------------------------------------------
# Sentinel-2 processing chain
# ---------------------------------------------------------------------------

S2_BANDS_EXPORT = [
    "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12",
    "NDVI", "BSI", "SAVI", "MSAVI2", "EVI2",
    "NDRE", "NDWI", "BI",
    "SI1", "SI2", "NDSI",
    "ClayIndex", "AlOH", "CarbonateIndex",
    "IronIndex", "FerrousIndex", "RI",
    "SWIR_ratio", "RedEdge_ratio", "CI_green",
]


def mask_s2_clouds(image: ee.Image) -> ee.Image:
    scl = image.select("SCL")
    good = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6))
    return image.updateMask(good).divide(10000).copyProperties(image, ["system:time_start"])


def filter_bare_soil(image: ee.Image) -> ee.Image:
    ndvi = image.normalizedDifference(["B8", "B4"])
    return image.updateMask(ndvi.lt(BARE_SOIL_NDVI_MAX))


def add_spectral_indices(image: ee.Image) -> ee.Image:
    b = {n: image.select(n) for n in ["B2", "B3", "B4", "B5", "B8", "B8A", "B11", "B12"]}
    blue, green, red, re1 = b["B2"], b["B3"], b["B4"], b["B5"]
    nir, swir1, swir2 = b["B8"], b["B11"], b["B12"]

    indices = {
        "NDVI":          nir.subtract(red).divide(nir.add(red)),
        "BSI":           swir1.add(red).subtract(nir.add(blue))
                             .divide(swir1.add(red).add(nir).add(blue)),
        "SAVI":          nir.subtract(red).divide(nir.add(red).add(0.5)).multiply(1.5),
        "MSAVI2":        nir.multiply(2).add(1).subtract(
                             nir.multiply(2).add(1).pow(2)
                                 .subtract(nir.subtract(red).multiply(8)).sqrt()
                         ).divide(2),
        "EVI2":          nir.subtract(red)
                             .divide(nir.add(red.multiply(2.4)).add(1)).multiply(2.5),
        "NDRE":          re1.subtract(red).divide(re1.add(red)),
        "NDWI":          green.subtract(nir).divide(green.add(nir)),
        "BI":            red.pow(2).add(green.pow(2)).add(nir.pow(2)).divide(3).sqrt(),
        "SI1":           green.multiply(red).sqrt(),
        "SI2":           swir1.subtract(nir).divide(swir1.add(nir)),
        "NDSI":          swir1.subtract(swir2).divide(swir1.add(swir2)),
        "ClayIndex":     swir1.divide(swir2),
        "AlOH":          swir1.divide(swir2),
        "CarbonateIndex":swir1.divide(swir2.add(nir.multiply(0.1))),
        "IronIndex":     red.divide(blue),
        "FerrousIndex":  nir.divide(swir1),
        "RI":            red.pow(2).divide(blue.multiply(green.pow(3))),
        "SWIR_ratio":    swir1.divide(swir2),
        "RedEdge_ratio": re1.divide(red),
        "CI_green":      nir.divide(green).subtract(1),
    }

    for name, img in indices.items():
        image = image.addBands(img.rename(name))
    return image


def build_s2_composite(aoi: ee.Geometry, window: dict) -> ee.Image:
    col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(window["start"], window["end"])
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .map(mask_s2_clouds)
        .map(filter_bare_soil)
        .map(add_spectral_indices)
    )
    n = col.size().getInfo()
    logger.info(f"  {window['label']}: {n} scenes after filtering")
    return col.median().clip(aoi)


# ---------------------------------------------------------------------------
# Terrain stack
# ---------------------------------------------------------------------------

def build_terrain_stack(aoi: ee.Geometry) -> ee.Image:
    dem = ee.Image("USGS/SRTMGL1_003").clip(aoi)
    slope      = ee.Terrain.slope(dem).rename("slope")
    aspect     = ee.Terrain.aspect(dem).rename("aspect")
    hillshade  = ee.Terrain.hillshade(dem).rename("hillshade")

    slope_rad  = slope.multiply(3.14159265 / 180).max(0.001)
    tan_slope  = slope_rad.tan().max(0.001)
    upslope    = dem.focalMean(radius=5, kernelType="square", units="pixels") \
                    .subtract(dem).abs().add(1)
    twi        = upslope.divide(tan_slope).log().rename("TWI")

    neighbours = dem.neighborhoodToBands(ee.Kernel.square(1))
    tri        = neighbours.subtract(dem).abs().reduce(ee.Reducer.mean()).rename("TRI")
    focal_mean = dem.focalMean(radius=10, kernelType="square", units="pixels")
    tpi        = dem.subtract(focal_mean).rename("TPI")
    curvature  = dem.convolve(ee.Kernel.laplacian8()).rename("curvature")

    return (
        dem.rename("elevation")
        .addBands(slope).addBands(aspect).addBands(hillshade)
        .addBands(curvature).addBands(twi).addBands(tri).addBands(tpi)
    )


# ---------------------------------------------------------------------------
# GEE export helpers
# ---------------------------------------------------------------------------

def submit_export(image: ee.Image, description: str, filename: str,
                  aoi: ee.Geometry, scale: int) -> ee.batch.Task:
    task = ee.batch.Export.image.toDrive(
        image=image.toFloat(),
        description=description,
        folder=GEE_DRIVE_FOLDER,
        fileNamePrefix=filename,
        region=aoi,
        scale=scale,
        crs=TARGET_CRS,
        maxPixels=int(1e10),
        fileFormat="GeoTIFF",
    )
    task.start()
    logger.info(f"Task submitted: {description}")
    return task


def wait_for_tasks(tasks: list[ee.batch.Task], poll_interval: int = 30):
    """Block until all EE tasks reach COMPLETED or FAILED."""
    pending = {t.id: t for t in tasks}
    while pending:
        time.sleep(poll_interval)
        still_running = {}
        for tid, task in pending.items():
            status = task.status()
            state  = status["state"]
            if state == "COMPLETED":
                logger.success(f"  ✓ {status['description']}")
            elif state == "FAILED":
                logger.error(f"  ✗ {status['description']}: {status.get('error_message')}")
            else:
                still_running[tid] = task
        pending = still_running
        if pending:
            logger.info(f"  {len(pending)} task(s) still running…")


# ---------------------------------------------------------------------------
# Google Drive download
# ---------------------------------------------------------------------------

def download_from_drive(filename_prefix: str, dest_dir: Path):
    """Download files matching prefix from Drive folder to dest_dir."""
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials

        creds = Credentials.from_authorized_user_file(
            Path.home() / ".config" / "earthengine" / "credentials"
        )
        drive = build("drive", "v3", credentials=creds)

        query = (
            f"name contains '{filename_prefix}' "
            f"and '{GEE_DRIVE_FOLDER}' in parents "
            f"and trashed = false"
        )
        results = drive.files().list(q=query, fields="files(id, name)").execute()
        files   = results.get("files", [])

        if not files:
            logger.warning(f"No Drive files found matching '{filename_prefix}'")
            return

        dest_dir.mkdir(parents=True, exist_ok=True)
        for f in files:
            dest = dest_dir / f["name"]
            if dest.exists():
                logger.info(f"  Already downloaded: {f['name']}")
                continue
            request = drive.files().get_media(fileId=f["id"])
            with open(dest, "wb") as fh:
                fh.write(request.execute())
            logger.success(f"  Downloaded: {f['name']} → {dest}")

    except Exception as exc:
        logger.warning(
            f"Drive download failed ({exc}). "
            f"Download manually from Google Drive folder: {GEE_DRIVE_FOLDER}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(district: str | None, skip_gee: bool):
    authenticate_gee()
    aoi = get_aoi(district)
    label = district or "AP"

    tasks = []

    if not skip_gee:
        logger.info("Building Sentinel-2 composites…")
        for window in BARE_SOIL_WINDOWS:
            composite = build_s2_composite(aoi, window)
            fname     = f"s2_baresoil_{label.lower()}_{window['label']}"
            task      = submit_export(
                composite.select(S2_BANDS_EXPORT),
                description=f"S2_Composite_{label}_{window['label']}",
                filename=fname,
                aoi=aoi,
                scale=10,
            )
            tasks.append(task)

        logger.info("Building terrain stack…")
        terrain = build_terrain_stack(aoi)
        tasks.append(submit_export(
            terrain,
            description=f"Terrain_{label}_SRTM",
            filename=f"terrain_{label.lower()}_srtm",
            aoi=aoi,
            scale=30,
        ))

        logger.info(f"Waiting for {len(tasks)} GEE task(s)…")
        wait_for_tasks(tasks)

    logger.info("Downloading from Google Drive…")
    s2_dir      = RAW_DIR / "sentinel2"
    terrain_dir = RAW_DIR / "dem"

    for window in BARE_SOIL_WINDOWS:
        download_from_drive(
            f"s2_baresoil_{label.lower()}_{window['label']}",
            s2_dir,
        )
    download_from_drive(f"terrain_{label.lower()}_srtm", terrain_dir)

    logger.success("Module 1 complete. Raw data in data/raw/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest satellite data via GEE")
    parser.add_argument("--district", default="Krishna",
                        help="District name (default: Krishna). Use 'AP' for full state.")
    parser.add_argument("--skip-gee", action="store_true",
                        help="Skip GEE export; only download already-completed tasks.")
    args = parser.parse_args()
    main(args.district if args.district != "AP" else None, args.skip_gee)
