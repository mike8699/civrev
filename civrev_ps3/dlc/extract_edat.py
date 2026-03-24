import argparse
import os
import subprocess
import sys
from pathlib import Path

make_npdata_dir = Path(__file__).parent / "make_npdata"

if os.name == "posix":
    make_npdata_binary = make_npdata_dir / "Linux" / "make_npdata"
else:
    raise NotImplementedError("Only Linux is supported.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script for decrypting .EDAT files in CivRev for PS3."
    )
    parser.add_argument("edat", type=str, help="Source .EDAT file.")
    parser.add_argument("rap", type=str, help="Source .RAP file for decryption.")
    parser.add_argument("output", type=str, help="Destination path for decrypted file.")

    parsed_args = parser.parse_args()
    src_edat = Path(parsed_args.edat)
    src_rap = Path(parsed_args.rap)
    dest_file = Path(parsed_args.output)

    if not src_edat.exists() or not src_edat.is_file():
        print(
            f"Source file {src_edat} does not exist or is not a file.", file=sys.stderr
        )
        sys.exit(1)
    elif not src_rap.exists() or not src_rap.is_file():
        print(
            f"Source RAP file {src_rap} does not exist or is not a file.",
            file=sys.stderr,
        )
        sys.exit(1)
    elif not dest_file.parent.exists():
        print(
            f"Destination directory {dest_file.parent} does not exist.", file=sys.stderr
        )
        sys.exit(1)

    if not make_npdata_binary.exists():
        print(f"make_npdata binary not found at {make_npdata_binary}.", file=sys.stderr)
        print("Attempting to build it...", file=sys.stderr)
        subprocess.run(["make", "-C", str(make_npdata_binary.parent)], check=True)

    args = [
        "-d",
        str(src_edat),
        str(dest_file),
        "klick",
        src_rap,
    ]

    print(f"Running make_npdata with arguments: {args}")
    result = subprocess.run(
        [str(make_npdata_binary)] + args, check=True, capture_output=True
    )

    if result.returncode != 0:
        print(f"Error running make_npdata: {result.stderr.decode()}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Decrypted file saved to {dest_file}.")
        print(f"Output: {result.stdout.decode()}")
