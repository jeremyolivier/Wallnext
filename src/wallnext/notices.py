"""Licenses of the software bundled with Wallnext (third-party notices).

Built from the installed packages' metadata. `just build` writes them next to
the exe as THIRD-PARTY-NOTICES.txt; from source, they are generated on the fly.

    python -m wallnext.notices <output file>
"""

import hashlib
import importlib.metadata as md
import platform
import re
import sys
from pathlib import Path

FILE_NAME = "THIRD-PARTY-NOTICES.txt"
# Repository folder holding license texts the packages themselves do not ship.
_LICENSES = Path(__file__).resolve().parents[2] / "licenses"
_LICENSE_FILE = re.compile(r"(LICEN[CS]E|COPYING|NOTICE)", re.IGNORECASE)

# PySide6 wheels only ship the Qt commercial terms; Wallnext uses the LGPLv3.
_LGPL = (
    (
        "Used under the GNU LGPL version 3, which includes the GPL version 3 "
        "below. It bundles the Qt 6 libraries (also LGPLv3), whose source code is "
        "at https://code.qt.io. The Qt and PySide6 DLLs in the installation "
        "folder can be replaced by other compatible builds."
    ),
    ["LGPL-3.0.txt", "GPL-3.0.txt"],
)
_OVERRIDES = {"pyside6-essentials": _LGPL, "shiboken6": _LGPL}
# Only Nuitka's runtime library ends up in the exe, under this exception.
_NUITKA_FILES = ("LICENSE-RUNTIME.txt", "NOTICE.txt")


def _key(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _runtime_distributions() -> list[md.Distribution]:
    """Wallnext's dependencies, recursively, without extras or dev tools."""
    found: dict[str, md.Distribution] = {}
    pending = ["wallnext"]
    while pending:
        name = pending.pop()
        if _key(name) in found:
            continue
        try:
            dist = md.distribution(name)
        except md.PackageNotFoundError:
            continue
        found[_key(name)] = dist
        for requirement in dist.requires or []:
            if "extra ==" not in requirement:
                pending.append(re.split(r"[\s<>=!~;\[(]", requirement, maxsplit=1)[0])
    found.pop("wallnext")
    return sorted(found.values(), key=lambda d: _key(d.metadata["Name"]))


def _license_name(dist: md.Distribution) -> str:
    meta = dist.metadata
    if expression := meta.get("License-Expression"):
        return expression
    classifiers = [
        c.split(" :: ")[-1]
        for c in meta.get_all("Classifier") or []
        if c.startswith("License ::")
    ]
    return ", ".join(classifiers) or (meta.get("License") or "").split("\n")[0]


def _license_texts(dist: md.Distribution, names: tuple[str, ...] = ()) -> list[str]:
    texts, seen = [], set()
    for file in dist.files or []:
        if not _LICENSE_FILE.search(file.name) or (names and file.name not in names):
            continue
        text = Path(str(dist.locate_file(file))).read_text("utf-8", "replace").strip()
        digest = hashlib.sha256(text.encode()).hexdigest()
        if digest not in seen:  # wheels often ship the same file twice
            seen.add(digest)
            texts.append(text)
    return texts


def _section(title: str, intro: str, texts: list[str]) -> str:
    body = "\n\n".join([intro, *texts]) if intro else "\n\n".join(texts)
    return f"{'=' * 79}\n{title}\n{'=' * 79}\n\n{body}\n"


def generate() -> str:
    sections = []
    for dist in _runtime_distributions():
        meta = dist.metadata
        title = f"{meta['Name']} {dist.version} — {_license_name(dist)}"
        if override := _OVERRIDES.get(_key(meta["Name"])):
            intro, files = override
            texts = [(_LICENSES / f).read_text("utf-8").strip() for f in files]
        else:
            intro, texts = "", _license_texts(dist)
        sections.append(_section(title, intro, texts))

    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        sections.append(
            _section(
                f"Python {platform.python_version()} — PSF-2.0",
                "",
                [python_license.read_text("utf-8", "replace").strip()],
            )
        )
    try:
        nuitka = md.distribution("nuitka")
    except md.PackageNotFoundError:
        pass
    else:
        sections.append(
            _section(
                f"Nuitka {nuitka.version} runtime library",
                "The exe is compiled with Nuitka. Only its runtime library is "
                "included, under the Nuitka Runtime Library Exception.",
                _license_texts(nuitka, _NUITKA_FILES),
            )
        )

    header = (
        "Wallnext includes the following third-party software, each under its "
        "own license.\n"
    )
    return header + "\n" + "\n".join(sections)


def text() -> str:
    """The notices shipped with the exe, or generated when run from source."""
    # Packaged, sys.executable is wallnext.exe; from source, the venv's python.
    bundled = Path(sys.executable).with_name(FILE_NAME)
    return bundled.read_text("utf-8") if bundled.exists() else generate()


def license_text() -> str:
    """Wallnext's own license, shipped as LICENSE.txt next to the exe."""
    bundled = Path(sys.executable).with_name("LICENSE.txt")
    source = _LICENSES.parent / "LICENSE"
    return (bundled if bundled.exists() else source).read_text("utf-8")


if __name__ == "__main__":
    Path(sys.argv[1]).write_text(generate(), encoding="utf-8")
