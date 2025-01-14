"""Fill bubble contours."""

from loguru import logger
from tqdm import tqdm
from xarray import zeros_like

from boilercv.data import ROI, VIDEO
from boilercv.data.packing import pack
from boilercv.data.sets import get_contours_df, get_dataset, process_datasets
from boilercv.images import scale_bool
from boilercv.images.cv import draw_contours
from boilercv.models.params import PARAMS
from boilercv.types import ArrInt


def main():
    destination = PARAMS.paths.filled
    with process_datasets(destination) as videos_to_process:
        for name in tqdm(videos_to_process):
            df = get_contours_df(name)
            source_ds = get_dataset(name)
            ds = zeros_like(source_ds, dtype=source_ds[VIDEO].dtype)
            video = ds[VIDEO]
            if not df.empty:
                for frame_num, frame in enumerate(video):
                    contours: list[ArrInt] = list(  # type: ignore  # pyright 1.1.333
                        df.loc[frame_num, :]
                        .groupby("contour")
                        .apply(lambda grp: grp.values)  # type: ignore  # pyright 1.1.333
                    )
                    video[frame_num, :, :] = draw_contours(
                        scale_bool(frame.values), contours
                    )
            ds[VIDEO] = pack(video)
            ds = ds.drop_vars(ROI)
            videos_to_process[name] = ds


if __name__ == "__main__":
    logger.info("Start filling contours")
    main()
    logger.info("Finish filling contours")
