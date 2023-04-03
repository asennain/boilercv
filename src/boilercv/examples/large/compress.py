"""Compress the video data in a NetCDF file.

Compression is slow for grayscale files of ~2GB size, but may work better for binarized
files.
"""

from boilercv.data import VIDEO
from boilercv.examples.large import example_dataset


@example_dataset(
    destination="compressed", preview=False, encoding={VIDEO: {"zlib": True}}
)
def main():
    pass


if __name__ == "__main__":
    main()