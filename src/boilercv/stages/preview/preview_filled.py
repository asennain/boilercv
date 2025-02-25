"""Update previews for the filled contours stage."""

from loguru import logger
from tqdm import tqdm

from boilercv.data import FRAME, VIDEO
from boilercv.data.sets import get_dataset
from boilercv.models.params import PARAMS
from boilercv.stages.preview import new_videos_to_preview


def main():
    stage = "filled"
    destination = PARAMS.paths.filled_preview
    with new_videos_to_preview(destination) as videos_to_preview:
        for video_name in tqdm(videos_to_preview):
            ds = get_dataset(video_name, stage=stage, num_frames=1)
            videos_to_preview[video_name] = ds[VIDEO].isel({FRAME: 0}).values


if __name__ == "__main__":
    logger.info("Start updating filled preview")
    main()
    logger.info("Finish updating filled preview")
