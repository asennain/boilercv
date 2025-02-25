"""Datasets."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal, TypeAlias

from pandas import read_hdf
from xarray import Dataset, open_dataset

from boilercv.data import HEADER, ROI, VIDEO
from boilercv.data.packing import unpack
from boilercv.models.params import PARAMS
from boilercv.models.paths import get_sorted_paths
from boilercv.types import DF, DS

ALL_FRAMES = slice(None)
"""Slice that gets all frames."""
ALL_STEMS = [source.stem for source in get_sorted_paths(PARAMS.paths.sources)]
"""The stems of all dataset sources."""
STAGE_DEFAULT = "sources"
"""Default stage to work on."""

Stage: TypeAlias = Literal["large_sources", "sources", "filled"]


@contextmanager
def process_datasets(
    destination_dir: Path, reprocess: bool = False
) -> Iterator[dict[str, Any]]:
    """Get unprocessed dataset names and write them to disk.

    Use as a context manager. Given a destination directory, yield a mapping with
    unprocessed dataset names as its keys. Upon exiting the context, datasets assigned
    to the values of the mapping will be written to disk in the destination directory.

    If no values are assigned to the yielded mapping, no datasets will be written. This
    is useful for processes which take input datasets but handle their own output,
    perhaps to a different file format.

    Args:
        destination_dir: The directory to write datasets to.
        reprocess: Whether to reprocess all datasets.
    """
    unprocessed_destinations = get_unprocessed_destinations(
        destination_dir, reprocess=reprocess
    )
    datasets_to_process = dict.fromkeys(unprocessed_destinations)
    yield datasets_to_process
    for name, ds in datasets_to_process.items():
        if ds is None:
            continue
        ds.to_netcdf(
            path=unprocessed_destinations[name], encoding={VIDEO: {"zlib": True}}
        )


def get_unprocessed_destinations(
    destination_dir: Path, ext: str = "nc", reprocess: bool = False
) -> dict[str, Path]:
    """Get destination paths for unprocessed datasets.

    Given a destination directory, yield a mapping of unprocessed dataset names to
    destinations with a given file extension. A dataset is considered unprocessed if a
    file sharing its name is not found in the destination directory.

    Args:
        destination_dir: The desired destination directory.
        ext: The desired file extension. Default: nc
        reprocess: Whether to reprocess all datasets. Default: False.

    Returns:
        A mapping of unprocessed dataset names to destinations with the given file
    """
    unprocessed_destinations: dict[str, Path] = {}
    ext = ext.lstrip(".")
    for name in ALL_STEMS:
        destination = destination_dir / f"{name}.{ext}"
        if reprocess or not destination.exists():
            unprocessed_destinations[name] = destination
    return unprocessed_destinations


def inspect_dataset(name: str, stage: Stage = STAGE_DEFAULT) -> DS:
    """Inspect a video dataset."""
    cmp_source, unc_source = get_stage(name, stage)
    source = unc_source if unc_source.exists() else cmp_source
    if stage == "large_sources":
        return open_dataset(source) if source.exists() else Dataset()
    with open_dataset(source) as ds:
        return ds


def get_dataset(
    name: str,
    num_frames: int = 0,
    frame: slice = ALL_FRAMES,
    stage: Stage = STAGE_DEFAULT,
) -> DS:
    """Load a video dataset."""
    # Can't use `xarray.open_mfdataset` because it requires dask
    # Unpacking is incompatible with dask
    frame = slice_frames(num_frames, frame)
    cmp_source, unc_source = get_stage(name, stage)
    source = unc_source if unc_source.exists() else cmp_source
    if stage == "large_sources":
        ds = open_dataset(source)
        return (
            Dataset({VIDEO: ds[VIDEO].sel(frame=frame), HEADER: ds[HEADER]})
            if source.exists()
            else Dataset()
        )
    roi = PARAMS.paths.rois / f"{name}.nc"
    with open_dataset(source) as ds, open_dataset(roi) as roi_ds:
        if not unc_source.exists():
            Dataset({VIDEO: ds[VIDEO], HEADER: ds[HEADER]}).to_netcdf(
                path=unc_source, encoding={VIDEO: {"zlib": False}}
            )
        return Dataset({
            VIDEO: unpack(ds[VIDEO].sel(frame=frame)),
            ROI: roi_ds[ROI],
            HEADER: ds[HEADER],
        })


def get_stage(name: str, stage: Stage = STAGE_DEFAULT) -> tuple[Path, Path]:
    """Get the paths associated with a particular video name and pipeline stage."""
    if stage == "sources":
        unc_source = PARAMS.paths.uncompressed_sources / f"{name}.nc"
        return PARAMS.paths.sources / f"{name}.nc", unc_source
    elif stage == "large_sources":
        source = unc_source = PARAMS.paths.large_sources / f"{name}.nc"
        return source, unc_source
    elif stage == "filled":
        unc_source = PARAMS.paths.uncompressed_filled / f"{name}.nc"
        return PARAMS.paths.filled / f"{name}.nc", unc_source
    else:
        raise ValueError(f"Unknown stage: {stage}")


def get_contours_df(name: str) -> DF:
    """Load contours from a dataset."""
    unc_cont = PARAMS.paths.uncompressed_contours / f"{name}.h5"
    contour = unc_cont if unc_cont.exists() else PARAMS.paths.contours / f"{name}.h5"
    contour_df: DF = read_hdf(contour)  # type: ignore  # pyright 1.1.333
    if not unc_cont.exists():
        contour_df.to_hdf(unc_cont, key="contours", complevel=None, complib=None)
    return contour_df


def slice_frames(num_frames: int = 0, frame: slice = ALL_FRAMES) -> slice:
    """Returns a slice suitable for getting frames from datasets."""
    if num_frames:
        if frame == ALL_FRAMES:
            frame = slice(None, num_frames - 1)
        else:
            raise ValueError("Don't specify both `num_frames` and `frame`.")
    return frame
