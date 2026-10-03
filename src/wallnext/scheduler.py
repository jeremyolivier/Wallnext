"""Register wallnext with the Windows Task Scheduler.

Task Scheduler owns the timing: a time trigger repeats indefinitely every
configured interval, and a logon trigger refreshes as soon as the user logs in.
Each run is a short-lived `wallnext set-random` — no resident process.

Uses the Task Scheduler COM API (`Schedule.Service`) through pywin32:
https://learn.microsoft.com/windows/win32/taskschd/task-scheduler-objects
"""

import math
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum
from pathlib import Path
from typing import Any

import pythoncom
import pywintypes
import win32api
import win32com.client
import win32con
import win32timezone  # noqa: F401 — lazily imported by pywin32, listed for Nuitka

from wallnext.exceptions import WallnextError

TASK_NAME = "wallnext"
TASK_ARGUMENTS = "set-random"


# Values from the Task Scheduler COM API (taskschd.h).
class _Trigger(IntEnum):
    TIME = 1
    LOGON = 9


class _Action(IntEnum):
    EXEC = 0


class _Logon(IntEnum):
    INTERACTIVE_TOKEN = 3


class _Instances(IntEnum):
    IGNORE_NEW = 2


class State(IntEnum):
    UNKNOWN = 0
    DISABLED = 1
    QUEUED = 2
    READY = 3
    RUNNING = 4


_CREATE_OR_UPDATE = 6
_TASK_NEVER_RUN = 0x41303  # SCHED_S_TASK_HAS_NOT_RUN
_NOT_FOUND = -2147024894  # HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND)


@dataclass(frozen=True)
class Status:
    state: State
    command: str
    last_run: datetime | None
    last_result: int | None
    next_run: datetime | None


@contextmanager
def _com_errors() -> Iterator[None]:
    """Turn COM failures into WallnextError with Windows' own message."""
    try:
        yield
    except pywintypes.com_error as e:
        # The meaningful HRESULT is in excepinfo; the outer one is a generic
        # "exception occurred".
        hresult, _, excepinfo, _ = e.args
        code = excepinfo[5] if excepinfo else hresult
        if code == _NOT_FOUND:
            raise WallnextError(
                "Schedule not installed — run `wallnext schedule install`."
            ) from e
        raise WallnextError(
            f"Task Scheduler: {win32api.FormatMessage(code).strip()}"
        ) from e


def _service() -> Any:
    pythoncom.CoInitialize()
    service = win32com.client.Dispatch("Schedule.Service")
    service.Connect()
    return service


def _root_folder() -> Any:
    return _service().GetFolder("\\")


def _get_task() -> Any:
    with _com_errors():
        return _root_folder().GetTask(TASK_NAME)


def _executable() -> Path:
    """The wallnext executable the task should run.

    When packaged with Nuitka, sys.executable is the wallnext executable; under
    `uv run` it is python.exe, so fall back to the console-script launcher in
    argv[0]. The path is deliberately not resolved: Scoop installs behind a
    `current` junction, and resolving it would pin the task to one version.
    """
    candidate = Path(sys.executable)
    if not candidate.stem.lower().startswith("wallnext"):
        candidate = Path(sys.argv[0])
        # The console-script launcher can show up in argv[0] without its suffix.
        if not candidate.suffix and candidate.with_suffix(".exe").exists():
            candidate = candidate.with_suffix(".exe")
    return candidate.absolute()


def _interval(seconds: int) -> str:
    # ISO 8601 duration; Task Scheduler repeats in whole minutes, 1 minute minimum.
    return f"PT{max(1, math.ceil(seconds / 60))}M"


def _date(value: datetime) -> datetime:
    # COM dates are local times that pywin32 mislabels as UTC: drop the tzinfo.
    return value.replace(tzinfo=None)


def _register(definition: Any) -> None:
    _root_folder().RegisterTaskDefinition(
        TASK_NAME,
        definition,
        _CREATE_OR_UPDATE,
        win32api.GetUserNameEx(win32con.NameSamCompatible),
        None,
        _Logon.INTERACTIVE_TOKEN,
    )


def is_installed() -> bool:
    try:
        _get_task()
    except WallnextError:
        return False
    return True


def install(interval_seconds: int) -> Path:
    """Register (or replace) the task. Returns the executable it will run."""
    exe = _executable()
    user = win32api.GetUserNameEx(win32con.NameSamCompatible)  # DOMAIN\user

    with _com_errors():
        service = _service()
        task = service.NewTask(0)

        task.RegistrationInfo.Description = "Wallnext wallpaper refresh"

        task.Principal.LogonType = (
            _Logon.INTERACTIVE_TOKEN
        )  # run in the user's desktop session

        settings = task.Settings
        settings.Hidden = True
        settings.StartWhenAvailable = True  # catch up on runs missed while asleep
        settings.RunOnlyIfNetworkAvailable = True
        settings.DisallowStartIfOnBatteries = False
        settings.StopIfGoingOnBatteries = False
        settings.ExecutionTimeLimit = "PT5M"  # kill a stuck download
        settings.MultipleInstances = _Instances.IGNORE_NEW

        every_interval = task.Triggers.Create(_Trigger.TIME)
        # No offset on purpose: Task Scheduler reads it as local time.
        every_interval.StartBoundary = datetime.now().isoformat(timespec="seconds")  # noqa: DTZ005
        every_interval.Repetition.Interval = _interval(interval_seconds)
        # Repetition.Duration left empty: repeat indefinitely.

        at_logon = task.Triggers.Create(_Trigger.LOGON)
        at_logon.UserId = user

        action = task.Actions.Create(_Action.EXEC)
        action.Path = str(exe)
        action.Arguments = TASK_ARGUMENTS

        _register(task)
    return exe


def set_interval(interval_seconds: int) -> None:
    """Update the interval in place, keeping the executable the task runs."""
    task = _get_task()
    with _com_errors():
        definition = task.Definition
        for index in range(1, definition.Triggers.Count + 1):
            trigger = definition.Triggers.Item(index)
            if trigger.Type == _Trigger.TIME:
                trigger.Repetition.Interval = _interval(interval_seconds)
        _register(definition)


def restart_countdown(interval_seconds: int) -> None:
    """Push the next scheduled refresh a full interval from now."""
    # A future start boundary: StartWhenAvailable sees no missed run.
    task = _get_task()
    start = datetime.now() + timedelta(seconds=interval_seconds)  # noqa: DTZ005
    with _com_errors():
        definition = task.Definition
        for index in range(1, definition.Triggers.Count + 1):
            trigger = definition.Triggers.Item(index)
            if trigger.Type == _Trigger.TIME:
                # No offset on purpose: Task Scheduler reads it as local time.
                trigger.StartBoundary = start.isoformat(timespec="seconds")
        _register(definition)


def uninstall() -> None:
    with _com_errors():
        _root_folder().DeleteTask(TASK_NAME, 0)


def start() -> None:
    """Resume scheduled refreshes and change the wallpaper right away."""
    task = _get_task()
    with _com_errors():
        task.Enabled = True
        task.Run(None)


def stop() -> None:
    """Pause scheduled refreshes until `start` is called again."""
    task = _get_task()
    with _com_errors():
        task.Enabled = False


def status() -> Status:
    task = _get_task()
    with _com_errors():
        action = task.Definition.Actions.Item(1)
        # Dates are placeholders until the task has run / while it is disabled.
        has_run = task.LastTaskResult != _TASK_NEVER_RUN
        return Status(
            state=State(task.State),
            command=f"{action.Path} {action.Arguments}",
            last_run=_date(task.LastRunTime) if has_run else None,
            last_result=task.LastTaskResult if has_run else None,
            next_run=_date(task.NextRunTime) if task.Enabled else None,
        )
