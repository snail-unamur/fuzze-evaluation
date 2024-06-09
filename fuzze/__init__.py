import datetime
import json
import logging
import os
import re
import shutil
import time
from typing import Any, Optional
from antlr4 import CommonTokenStream, FileStream
import jsbeautifier
from fuzze.tours.fuzz_pickers import PickerABC
from fuzze.tours.parsing import (
    FuzzedFilesDataCollection,
    FuzzedTourData,
    format_tour_name,
)
from fuzze.tours.parsing.generated.JavaScriptLexer import JavaScriptLexer
from fuzze.tours.parsing.generated.JavaScriptParser import JavaScriptParser
from fuzze.tours.parsing import FuzzData, FuzzTourTextVisitor
from pathlib import Path

RE_GET_TOUR_FAILURE = re.compile(
    r".*Tour (.+) failed at step (.+\(trigger: (.+)\)|.+)", re.MULTILINE
)
RE_TOUR_SETUP_FAILURE = re.compile(
    r"""False is not true : The ready "odoo.isTourReady\(.*\)" code was always falsy"""
)


def test_tour_fuzze(test_case, url_path, tour_name, login="admin", **kwargs):
    """Inner func for a fuzzee subtest. This function is
    intended to be used as a subtest in a fuzzing test case.

    Args:
        test_case (odoo.HttpCase): The test case instance.
        url: The URL to start the tour.
        name: The name of the tour.
        login: The login to use for the tour.
        **kwargs: Additional arguments to pass to the start_tour method.

    Returns:
        Optional[tuple[str, str]]: The step that failed, if any.
    """
    trace: tuple[str, str] | None = None

    logger: logging.Logger = kwargs.get("logger", logging.getLogger(__name__))
    try:
        test_case.start_tour(
            url_path=url_path,
            tour_name=tour_name,
            login=login,
            **kwargs,
        )
    except AssertionError as e:
        setup_match = re.match(RE_TOUR_SETUP_FAILURE, str(e))
        if setup_match is not None:
            logger.error(f"Tour {tour_name} setup failed - skipping: {str(e)}")
            raise test_case.SkipTest()
        match = re.findall(RE_GET_TOUR_FAILURE, str(e))
        if len(match) > 0:
            tour, full_step, step = match[0]
            if step == "" or step is None:
                step = full_step
            logger.error(f"Tour {tour_name} failed at step {step}")
            trace = (tour, step)

            e.add_note(
                json.dumps(
                    {
                        "tour": tour_name,
                        "context": trace,
                    }
                )
            )
        raise
    finally:
        return trace


def get_tour_path(name: str, addon_path: Path) -> str:
    path = find_tour(name, str(addon_path))
    if path is None:
        raise FileNotFoundError(f"Tour {name} not found in {addon_path}")
    return path


TOUR_PATH_TEMPLATE = Path("static", "tests", "tours")


def fuzz(name, tour_path: Path, addon_path: Path, strategy: PickerABC, clean=False):
    filename = os.path.basename(tour_path)
    input_stream = FileStream(str(tour_path.absolute()))
    lexer = JavaScriptLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = JavaScriptParser(token_stream)
    fuzzer = FuzzTourTextVisitor(name, strategy)
    fuzzs = fuzzer.visit(parser.program())
    gen_path = os.path.join(addon_path, TOUR_PATH_TEMPLATE, "generated")
    if clean:
        shutil.rmtree(gen_path)
    os.makedirs(gen_path, exist_ok=True)
    os.makedirs(os.path.join(addon_path, "failed"), exist_ok=True)
    os.makedirs(os.path.join(addon_path, TOUR_PATH_TEMPLATE, "report"), exist_ok=True)
    names: list[str] = []
    for i, f in enumerate(fuzzs):
        name = format_tour_name(fuzzer.tour_name, i)
        names.append(name)
        filepath = os.path.join(gen_path, filename.replace(".js", f"_{i}.js"))
        fuzzer.fuzz_data[name].path = filepath
        __save(filepath, jsbeautifier.beautify(f))
    make_backup_filesys(addon_path)
    fuzzer.fuzz_data.save(os.path.join(gen_path, "fuzz_data.json"))


def __save(file, content):
    with open(file, "w") as f:
        f.write(content)


def find_tour(name: str, path: str) -> Optional[str]:
    if os.path.isfile(path):
        return path if path.endswith(name) else None
    if path.endswith("generated"):
        return None
    for f in os.listdir(path):
        if f.endswith(name):
            return os.path.join(path, f)
        deeper = find_tour(name, os.path.join(path, f))
        if deeper is not None:
            return deeper
    return None


def backup_tour(source, dest):
    with open(source, "r") as f:
        content = f.read()
    with open(dest, "w") as f:
        f.write(content)


def load_fuzz_data(path: Path) -> FuzzedFilesDataCollection:
    def t(d: dict):
        d.pop("filename", None)
        p = d.pop("path", None)
        return FuzzedTourData(mk_fuzz_data(d), path=p)

    with open(path) as f:
        data = json.load(f)
        return FuzzedFilesDataCollection({k: t(v) for k, v in data.items()})


def mk_fuzz_data(data: dict[str, list[dict[str, Any]]]):
    return {k: [FuzzData(**v) for v in c] for k, c in data.items()}


def get_last_backup_path(root_dir: str | Path):
    """Get the last backup path for the given root directory.
    Root directory is the root of the addon where the tours are located.

    Args:
        root_dir (str | Path): The root directory of the addon.

    Returns:
        Path: The last backup path.

    Raises:
        FileNotFoundError: If no indexed backup directory is found.
    """
    i = get_available_index(root_dir) - 1
    if i == -1:
        raise FileNotFoundError("No backup directory found.")
    return __path_helper(root_dir) / str(i)


def get_available_index(root_dir: str | Path):
    """Get the first available index for the backup path in the given root directory.
    Root directory is the root of the addon where the tours are located. Backup directory
    must exists.

    Note:
        This function uses binary search to find the first available index.

    Args:
        root_dir (str | Path): The root directory of the addon.

    Returns:
        int: The first available index for the backup path.

    Raises:
        AssertionError: If the backup directory does not exist.
    """
    base = __path_helper(root_dir)
    assert base.exists(), f"Backup directory {base} does not exist."
    i = 1
    while (base / str(i)).exists():
        i = i * 2

    # Last available path is between i // 2 and i
    start, end = i // 2, i
    while start + 1 < end:
        mid = (start + end) // 2

        if (base / str(mid)).exists():
            start = mid
        else:
            end = mid

    return end


def __path_helper(root_dir: str | Path):
    return Path(root_dir) / "backup" / "failed"


def get_last_report_path(root_dir: str | Path):
    """Get the report directory path for the given root directory.
    Root directory is the root of the addon where the tours are located.

    Args:
        root_dir (str | Path): The root directory of the addon.

    Returns:
        Path: The report directory path.
    """
    return get_last_backup_path(root_dir) / "report"


def make_backup_filesys(root_dir: str | Path):
    """Make a backup of the failed tours in the given root directory.
    Root directory should be the root of the addon where the tours are located.

    Args:
        root_dir (str | Path): The root directory of the addon.

    Returns:
        Path: The backup directory path.
    """
    p = __path_helper(root_dir)
    p = p / str(get_available_index(root_dir)) / "report"
    if not p.exists():
        p.mkdir(parents=True)
    return p.parent
