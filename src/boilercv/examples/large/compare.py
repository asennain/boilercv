"""Compare the original binarized dataset with the round-tripped dataset."""

from typing import TypedDict

from boilercv import DEBUG
from boilercv.examples.large import example_dataset as ex_ds


class KW(TypedDict):
    preview: bool
    save: bool


kw = KW(preview=DEBUG, save=False)


def main():
    with ex_ds("binarized", **kw) as original, ex_ds("unpacked", **kw) as unpacked:
        assert unpacked.identical(original)  # noqa: S101


if __name__ == "__main__":
    main()
