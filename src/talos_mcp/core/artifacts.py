"""Platform-specific verification for private artifact storage."""

import ctypes
import os
from ctypes import wintypes
from pathlib import Path
from typing import Any, cast


def has_reparse_component(path: Path) -> bool:
    """Reject links and Windows reparse points anywhere in an artifact path."""
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            return True
        if os.name == "nt":
            kernel = cast("Any", ctypes).WinDLL("kernel32", use_last_error=True)
            kernel.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
            kernel.GetFileAttributesW.restype = wintypes.DWORD
            attributes = kernel.GetFileAttributesW(str(current))
            if attributes != 0xFFFFFFFF and attributes & 0x400:
                return True
    return False


def _acl_libraries() -> tuple[Any, Any]:
    """Bind only the Win32 calls needed for read-only ACL inspection."""
    advapi = cast("Any", ctypes).WinDLL("advapi32", use_last_error=True)
    kernel = cast("Any", ctypes).WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.c_void_p
    advapi.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(pointer),
        ctypes.POINTER(pointer),
        ctypes.POINTER(pointer),
        ctypes.POINTER(pointer),
        ctypes.POINTER(pointer),
    ]
    advapi.GetNamedSecurityInfoW.restype = wintypes.DWORD
    advapi.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        pointer,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.GetAce.argtypes = [pointer, wintypes.DWORD, ctypes.POINTER(pointer)]
    advapi.GetAce.restype = wintypes.BOOL
    advapi.EqualSid.argtypes = [pointer, pointer]
    advapi.EqualSid.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer
    advapi.ConvertSidToStringSidW.argtypes = [pointer, ctypes.POINTER(pointer)]
    advapi.ConvertSidToStringSidW.restype = wintypes.BOOL
    return advapi, kernel


def _current_user_sid(advapi: Any, kernel: Any, token: wintypes.HANDLE) -> tuple[int | None, Any]:
    """Return the SID and its backing buffer while the caller holds the token."""
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x8, ctypes.byref(token)):
        return None, None
    required = wintypes.DWORD()
    advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(required))
    if not required.value:
        return None, None
    token_user = ctypes.create_string_buffer(required.value)
    if not advapi.GetTokenInformation(token, 1, token_user, required, ctypes.byref(required)):
        return None, None
    return ctypes.c_void_p.from_buffer(token_user).value, token_user


def _private_dacl(advapi: Any, kernel: Any, dacl: ctypes.c_void_p, user_sid: int) -> bool:
    """Accept only ordinary user, SYSTEM, administrators, and owner-rights ACEs."""
    acl_header = ctypes.string_at(dacl, 8)
    count = int.from_bytes(acl_header[4:6], "little")
    found_user = False
    found_owner_rights = False
    for index in range(count):
        ace = ctypes.c_void_p()
        if not advapi.GetAce(dacl, index, ctypes.byref(ace)) or not ace.value:
            return False
        header = ctypes.string_at(ace, 4)
        if header[0] != 0:  # Only conventional ACCESS_ALLOWED_ACE is accepted.
            return False
        sid = ctypes.c_void_p(ace.value + 8)
        if advapi.EqualSid(sid, ctypes.c_void_p(user_sid)):
            found_user = True
            continue
        sid_text = ctypes.c_void_p()
        if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(sid_text)):
            return False
        try:
            name = ctypes.wstring_at(sid_text)
        finally:
            kernel.LocalFree(sid_text)
        # Local administrators already have recovery privileges; OWNER RIGHTS
        # applies only to the verified current-account owner.
        if name == "S-1-3-4":
            found_owner_rights = True
        if name not in {"S-1-5-18", "S-1-5-32-544", "S-1-3-4"}:
            return False
    return found_user or found_owner_rights


def windows_private_acl(path: Path) -> bool:
    """Require a DACL granting access only to the current account and Windows SYSTEM.

    Unknown ACE types and inherited broad grants fail closed. This reads the native
    ACL; it does not change operator-owned directory permissions.
    """
    if os.name != "nt":
        raise RuntimeError("Windows ACL check on non-Windows host")
    advapi, kernel = _acl_libraries()
    security_descriptor = ctypes.c_void_p()
    owner = ctypes.c_void_p()
    dacl = ctypes.c_void_p()
    result = advapi.GetNamedSecurityInfoW(
        ctypes.c_wchar_p(str(path)),
        1,
        0x5,
        ctypes.byref(owner),
        None,
        ctypes.byref(dacl),
        None,
        ctypes.byref(security_descriptor),
    )
    if result != 0 or not dacl.value or not owner.value:
        return False
    token = wintypes.HANDLE()
    try:
        user_sid, token_user = _current_user_sid(advapi, kernel, token)
        return bool(
            token_user is not None
            and user_sid
            and advapi.EqualSid(owner, ctypes.c_void_p(user_sid))
            and _private_dacl(advapi, kernel, dacl, user_sid)
        )
    finally:
        if token.value:
            kernel.CloseHandle(token)
        if security_descriptor.value:
            kernel.LocalFree(security_descriptor)
