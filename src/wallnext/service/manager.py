import os
import subprocess
import sys
import tempfile
from pathlib import Path

from wallnext.exceptions import WallnextError

TASK_NAME = "wallnext"

_TASK_XML = """<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Wallnext background wallpaper agent</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>{user}</UserId>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>{user}</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>true</Hidden>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{command}</Command>
      <Arguments>{arguments}</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def _current_user() -> str:
    domain = os.environ.get("USERDOMAIN", "")
    user = os.environ["USERNAME"]
    return f"{domain}\\{user}" if domain else user


def _agent_command() -> tuple[str, str]:
    """Path + arguments the scheduled task should run.

    When packaged with Nuitka, both sys.executable and argv[0] point at the
    wallnext executable, so the task invokes `<exe> service run`. Prefer
    sys.executable when it is the wallnext binary (frozen build).
    """
    candidate = Path(sys.executable)
    if not candidate.stem.lower().startswith("wallnext"):
        candidate = Path(sys.argv[0])
    return str(candidate.resolve()), "service run"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise WallnextError(
            f"{' '.join(args)} failed ({result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}"
        )
    return result


def install() -> None:
    command, arguments = _agent_command()
    xml = _TASK_XML.format(
        user=_current_user(), command=command, arguments=arguments
    )
    # schtasks /XML expects a UTF-16 encoded file.
    with tempfile.NamedTemporaryFile(
        "w", suffix=".xml", delete=False, encoding="utf-16"
    ) as f:
        f.write(xml)
        xml_path = f.name
    try:
        _run(["schtasks", "/Create", "/TN", TASK_NAME, "/XML", xml_path, "/F"])
    finally:
        os.unlink(xml_path)


def uninstall() -> None:
    _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])


def start() -> None:
    _run(["schtasks", "/Run", "/TN", TASK_NAME])


def stop() -> None:
    _run(["schtasks", "/End", "/TN", TASK_NAME])


def status() -> str:
    return _run(["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST"]).stdout
