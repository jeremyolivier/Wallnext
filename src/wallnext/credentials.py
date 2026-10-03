"""Secrets (API keys) kept in the Windows Credential Manager, not in config.toml.

Each one is a generic credential named "wallnext/<name>", visible under
Control Panel > Credential Manager > Windows Credentials.
"""

import pywintypes
import win32cred

_ERROR_NOT_FOUND = 1168


def _target(name: str) -> str:
    return f"wallnext/{name}"


def get(name: str) -> str:
    """The stored secret, or "" when there is none."""
    try:
        credential = win32cred.CredRead(_target(name), win32cred.CRED_TYPE_GENERIC)
    except pywintypes.error as e:
        if e.winerror == _ERROR_NOT_FOUND:
            return ""
        raise
    return credential["CredentialBlob"].decode("utf-16-le")


def put(name: str, secret: str) -> None:
    """Store `secret`, or delete the stored one when `secret` is empty."""
    if not secret:
        try:
            win32cred.CredDelete(_target(name), win32cred.CRED_TYPE_GENERIC)
        except pywintypes.error as e:
            if e.winerror != _ERROR_NOT_FOUND:
                raise
        return
    win32cred.CredWrite(
        {
            "Type": win32cred.CRED_TYPE_GENERIC,
            "TargetName": _target(name),
            "UserName": name,
            "CredentialBlob": secret,
            "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
        },
        0,
    )
