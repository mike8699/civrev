import runpy
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        dlc_dir = Path(__file__).parent
    else:
        dlc_dir = Path(sys.argv[1])

    for dlc_file in dlc_dir.rglob("*.pkg"):
        print(f"Processing {dlc_file}")
        sys.argv = []
        sys.argv.append("")

        rap_files = list(dlc_file.parent.glob("*.rap"))
        if rap_files:
            sys.argv += ["--rapkey", str(rap_files[0])]

        sys.argv += [
            "--",
            str(dlc_file),
        ]

        runpy.run_module(
            mod_name="PSN_get_pkg_info.PSN_get_pkg_info",
            run_name="__main__",
            alter_sys=True,
        )


if __name__ == "__main__":
    main()
