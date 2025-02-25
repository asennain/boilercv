"""Update previews for the binarization stage."""

from loguru import logger
from tqdm import tqdm

from boilercv.data import FRAME, ROI, VIDEO
from boilercv.data.sets import get_dataset
from boilercv.models.params import PARAMS
from boilercv.stages.preview import new_videos_to_preview


def main():
    stage = "sources"
    destination = PARAMS.paths.binarized_preview
    with new_videos_to_preview(destination) as videos_to_preview:
        for video_name in tqdm(videos_to_preview):
            ds = get_dataset(video_name, stage=stage, num_frames=1)
            first_frame = ds[VIDEO].isel({FRAME: 0}).values
            videos_to_preview[video_name] = first_frame & ds[ROI].values


if __name__ == "__main__":
    logger.info("Start updating binarized preview")
    main()
    logger.info("Finish updating binarized preview")
