import sys

from rich.console import Console

# Windows consoles default to cp1252, which can't encode glyphs such as "✓"/"✗"
# used in our output and makes rich raise UnicodeEncodeError. Force UTF-8 on the
# standard streams so output never crashes on these characters.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

console = Console()
err_console = Console(stderr=True)
