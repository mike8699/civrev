import argparse
import json
import logging
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    filename: str
    offset: int
    size: int
    additional_data: bytearray


class FPK:
    MAGIC_BYTES = b"\x06\x00\x00\x00FPK_\x00\x00"
    EXTRA_DATA_FILE_EXTENSION = "extradata"
    ORDERING_FILENAME = "ordering.json"

    def __init__(self, fpk_file: Path):
        self.fpk_file: Path = fpk_file
        self.file_entries: list[FileEntry] = []

        with open(self.fpk_file, "rb") as f:
            magic: bytes
            item_count: int
            magic, item_count = struct.unpack("<10s I", f.read(0xE))

            assert magic == self.MAGIC_BYTES, "Not a valid FPK file!"

            for _ in range(item_count):
                item_name_len: int = struct.unpack("<I", f.read(4))[0]
                logger.debug(f"Item name length: {hex(item_name_len)}")
                item_name = f.read(item_name_len).decode()
                logger.debug(f"Item name: {item_name}")

                zeroes_encountered = 0
                additional_data: bytearray = bytearray()
                while zeroes_encountered < 4:
                    if (d := f.read(1)) == b"\x00":
                        zeroes_encountered += 1
                    else:
                        zeroes_encountered = 0
                    additional_data.extend(d)

                file_size, file_offset = struct.unpack("<II", f.read(8))
                logger.debug(f"File size: {hex(file_size)}")
                logger.debug(f"File offset: {hex(file_offset)}")

                self.file_entries.append(
                    FileEntry(item_name, file_offset, file_size, additional_data)
                )

    def extract(self, dest_dir: Path):
        dest_dir.mkdir(parents=True, exist_ok=True)
        for entry in self.file_entries:
            with open(dest_dir / entry.filename, "wb") as out_file, open(
                dest_dir / f"{entry.filename}.{self.EXTRA_DATA_FILE_EXTENSION}", "wb"
            ) as meta_file:
                meta_file.write(entry.additional_data)
                with open(self.fpk_file, "rb") as f:
                    f.seek(entry.offset)
                    data = f.read(entry.size)
                    out_file.write(data)

        (dest_dir / self.ORDERING_FILENAME).write_text(
            json.dumps([entry.filename for entry in self.file_entries])
        )

    @classmethod
    def from_directory(cls, directory: Path):
        fpk_file = directory.parent / (directory.name + ".FPK")

        files = list(directory.iterdir())

        items_count = len(
            [
                f
                for f in files
                if not f.name.endswith(cls.EXTRA_DATA_FILE_EXTENSION)
                and not f.name == cls.ORDERING_FILENAME
            ]
        )

        filenames: list[str] = json.loads(
            (directory / cls.ORDERING_FILENAME).read_text()
        )
        assert isinstance(
            filenames, list
        ), f"Ordering file {cls.ORDERING_FILENAME} is not a list."
        assert len(filenames) == items_count, (
            f"Ordering file {cls.ORDERING_FILENAME} ({len(filenames)})does not match the number of "
            f"files in the directory ({items_count})."
        )

        with open(fpk_file, "wb") as fpk:
            fpk.write(cls.MAGIC_BYTES)  # Write the magic bytes
            fpk.write(struct.pack("<I", items_count))  # Write the item count

            offset_placeholder = b"\x00\x00\x00\x00"
            offsets_to_go_back_to: dict[str, int] = {}

            for filename in filenames:
                file = directory / filename

                if file.is_dir():
                    raise NotImplementedError
                if file.suffix == cls.EXTRA_DATA_FILE_EXTENSION:
                    logger.debug(f"Skipping {file} as it is an extra data file.")
                    continue

                extra_data_file = file.with_suffix(
                    f"{file.suffix}.{cls.EXTRA_DATA_FILE_EXTENSION}"
                )
                if not extra_data_file.exists():
                    raise Exception(
                        f"Extra data file {extra_data_file} does not exist for {file}."
                    )

                # Write the length of the filename
                fpk.write(struct.pack("<I", len(file.name)))
                # Write the filename
                fpk.write(file.name.encode())
                # Write the additional data
                fpk.write(extra_data_file.read_bytes())
                # Write the file size
                fpk.write(file.stat().st_size.to_bytes(4, "little"))
                # Write 4 zeroes as a placeholder for offset. We'll fill this in
                # later using the offsets_to_go_back_to dictionary.
                offsets_to_go_back_to[file.name] = fpk.tell()
                fpk.write(offset_placeholder)

            for filename, offset in offsets_to_go_back_to.items():
                file = directory / filename

                file_offset = fpk.tell()
                fpk.write(file.read_bytes())  # Write the file data

                current_position = fpk.tell()

                fpk.seek(offset)
                fpk.write(file_offset.to_bytes(4, "little"))

                fpk.seek(current_position)


def main() -> None:
    parser = argparse.ArgumentParser(description="FPK file extractor/repacker.")
    parser.add_argument(
        "mode",
        type=str,
        choices=["extract", "repack"],
        help="Mode to run the tool in: extract or repack.",
    )
    parser.add_argument(
        "src", type=str, help="Source FPK file or directory to extract/repack."
    )

    parsed_args = parser.parse_args()
    src_file = Path(parsed_args.src)
    mode: Literal["extract", "repack"] = parsed_args.mode

    if not src_file.exists():
        logger.info(f"File {src_file} does not exist.")
        return

    if mode == "extract":
        if src_file.is_file():
            dest = Path.cwd() / src_file.stem
            dest.mkdir(parents=True, exist_ok=True)
            logger.info(f"Extracting {src_file.name} to {dest}...")
            fpk = FPK(src_file)
            fpk.extract(dest_dir=dest)
        elif src_file.is_dir():
            logger.info(f"Extracting all FPK files in directory {src_file}...")
            for fpk_file in src_file.glob("*.FPK"):
                dest = Path.cwd() / "extracted" / fpk_file.stem
                dest.mkdir(parents=True, exist_ok=True)
                logger.info(f"\tExtracting {fpk_file.name} to {dest}...")
                fpk = FPK(fpk_file)
                fpk.extract(dest_dir=dest)

    elif mode == "repack":
        if not src_file.is_dir():
            raise Exception(f"Source {src_file} must be a directory for repacking.")

        FPK.from_directory(src_file)

    else:
        raise NotImplementedError()


if __name__ == "__main__":
    main()
