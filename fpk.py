import logging
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    filename: str
    offset: int
    size: int


class FPK:
    def __init__(self, fpk_file: Path):
        self.fpk_file: Path = fpk_file
        self.file_entries: list[FileEntry] = []

        with open(self.fpk_file, "rb") as f:
            magic: bytes
            item_count: int
            magic, item_count = struct.unpack("<10s I", f.read(0xE))

            assert magic == b"\x06\x00\x00\x00FPK_\x00\x00", "Not a valid FPK file!"

            for _ in range(item_count):
                item_name_len: int = struct.unpack("<I", f.read(4))[0]
                logger.debug(f"Item name length: {hex(item_name_len)}")
                item_name = f.read(item_name_len).decode()
                logger.debug(f"Item name: {item_name}")

                zeroes_encountered = 0
                while zeroes_encountered < 4:
                    if f.read(1) == b"\x00":
                        zeroes_encountered += 1
                    else:
                        zeroes_encountered = 0

                file_size, file_offset = struct.unpack("<II", f.read(8))
                logger.debug(f"File size: {hex(file_size)}")
                logger.debug(f"File offset: {hex(file_offset)}")

                self.file_entries.append(FileEntry(item_name, file_offset, file_size))

    def extract(self, dest_dir: Path):
        dest_dir.mkdir(parents=True, exist_ok=True)
        for entry in self.file_entries:
            with open(dest_dir / entry.filename, "wb") as out_file:
                with open(self.fpk_file, "rb") as f:
                    f.seek(entry.offset)
                    data = f.read(entry.size)
                    out_file.write(data)


def main():
    src_file = Path(sys.argv[1])

    if not src_file.exists():
        logger.info(f"File {src_file} does not exist.")
        return

    elif src_file.is_file():
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


if __name__ == "__main__":
    sys.exit(main())
