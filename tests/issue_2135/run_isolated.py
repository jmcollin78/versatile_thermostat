"""Run only this harness behind a fail-closed Linux seccomp network barrier.

No external sockets can be created or connected, including loopback and Unix
endpoints. AF_UNIX socketpairs remain available for asyncio's wakeup pipe.
This process does not start, connect to, or configure a Home Assistant server.
"""

from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path
import socket
import stat
import sys


ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = ROOT / "tests" / "issue_2135"
SCMP_ACT_ALLOW = 0x7FFF0000
SCMP_ACT_ERRNO = 0x00050000 | errno.EPERM
SCMP_CMP_NE = 1
SCMP_CMP_MASKED_EQ = 7


class ArgCompare(ctypes.Structure):
    _fields_ = [("arg", ctypes.c_uint), ("op", ctypes.c_int),
                ("datum_a", ctypes.c_uint64), ("datum_b", ctypes.c_uint64)]


def install_network_barrier() -> None:
    """Deny socket/connect and non-Unix socketpair in this process and children."""
    seccomp = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    seccomp.seccomp_init.argtypes = [ctypes.c_uint32]
    seccomp.seccomp_init.restype = ctypes.c_void_p
    seccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    seccomp.seccomp_syscall_resolve_name.restype = ctypes.c_int
    seccomp.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                               ctypes.c_int, ctypes.c_uint,
                                               ctypes.POINTER(ArgCompare)]
    seccomp.seccomp_rule_add_array.restype = ctypes.c_int
    seccomp.seccomp_load.argtypes = [ctypes.c_void_p]
    seccomp.seccomp_load.restype = ctypes.c_int
    seccomp.seccomp_release.argtypes = [ctypes.c_void_p]
    ctx = seccomp.seccomp_init(SCMP_ACT_ALLOW)
    if not ctx:
        raise RuntimeError("seccomp_init failed")
    try:
        for name in (b"socket", b"connect", b"io_uring_setup", b"io_uring_enter",
                 b"io_uring_register", b"pidfd_getfd"):
            nr = seccomp.seccomp_syscall_resolve_name(name)
            if nr < 0 or seccomp.seccomp_rule_add_array(ctx, SCMP_ACT_ERRNO, nr, 0, None):
                raise RuntimeError(f"cannot deny {name!r}")
        nr = seccomp.seccomp_syscall_resolve_name(b"socketpair")
        comparison = ArgCompare(0, SCMP_CMP_NE, socket.AF_UNIX, 0)
        if nr < 0 or seccomp.seccomp_rule_add_array(ctx, SCMP_ACT_ERRNO, nr, 1, ctypes.byref(comparison)):
            raise RuntimeError("cannot restrict socketpair")
        # A Unix datagram socketpair can sendto a third-party Unix endpoint.
        # Permit only SOCK_STREAM, ignoring NONBLOCK/CLOEXEC flag bits.
        for kind in range(16):
            if kind == socket.SOCK_STREAM:
                continue
            comparison = ArgCompare(1, SCMP_CMP_MASKED_EQ, 15, kind)
            if seccomp.seccomp_rule_add_array(ctx, SCMP_ACT_ERRNO, nr, 1, ctypes.byref(comparison)):
                raise RuntimeError("cannot restrict socketpair type")
        if seccomp.seccomp_load(ctx):
            raise RuntimeError("seccomp_load failed")
    finally:
        seccomp.seccomp_release(ctx)


def assert_network_barrier() -> None:
    """Probe actual syscalls, not pytest-socket's Python-level monkeypatch."""
    libc = ctypes.CDLL(None, use_errno=True)
    libc.socket.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
    libc.socket.restype = ctypes.c_int
    for family in (socket.AF_INET, socket.AF_INET6, socket.AF_UNIX):
        ctypes.set_errno(0)
        fd = libc.socket(family, socket.SOCK_STREAM, 0)
        if fd != -1 or ctypes.get_errno() != errno.EPERM:
            if fd >= 0:
                os.close(fd)
            raise RuntimeError(f"socket family {family} not blocked by kernel")
    seccomp = ctypes.CDLL("libseccomp.so.2")
    seccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    seccomp.seccomp_syscall_resolve_name.restype = ctypes.c_int
    libc.syscall.restype = ctypes.c_long
    for name in (b"io_uring_setup", b"io_uring_enter", b"io_uring_register", b"pidfd_getfd"):
        nr = seccomp.seccomp_syscall_resolve_name(name)
        ctypes.set_errno(0)
        if nr < 0 or libc.syscall(nr, 0, 0, 0, 0, 0, 0) != -1 or ctypes.get_errno() != errno.EPERM:
            raise RuntimeError(f"{name!r} not blocked by kernel")
    pair = (ctypes.c_int * 2)()
    ctypes.set_errno(0)
    if libc.socketpair(socket.AF_INET, socket.SOCK_STREAM, 0, pair) != -1 or ctypes.get_errno() != errno.EPERM:
        raise RuntimeError("non-Unix socketpair not blocked by kernel")
    ctypes.set_errno(0)
    if libc.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM, 0, pair) != -1 or ctypes.get_errno() != errno.EPERM:
        raise RuntimeError("Unix datagram socketpair not blocked by kernel")
    if libc.socketpair(socket.AF_UNIX, socket.SOCK_STREAM, 0, pair) != 0:
        raise RuntimeError("asyncio Unix socketpair unavailable")
    try:
        ctypes.set_errno(0)
        if libc.connect(pair[0], None, 0) != -1 or ctypes.get_errno() != errno.EPERM:
            raise RuntimeError("connect not blocked by kernel")
    finally:
        os.close(pair[0])
        os.close(pair[1])


def main() -> None:
    if sys.platform != "linux" or sys.argv[1:] not in ([], ["--self-check"]):
        raise SystemExit("Linux only; accepted argument: --self-check")
    for fd in range(3):
        if stat.S_ISSOCK(os.fstat(fd).st_mode):
            raise SystemExit("socket inherited through standard streams")
    # Do not inherit a pre-connected descriptor, even through subprocesses.
    for name in os.listdir("/proc/self/fd"):
        fd = int(name)
        if fd > 2:
            try:
                os.close(fd)
            except OSError:
                pass
    install_network_barrier()
    assert_network_barrier()
    print("ISOLATION: socket/connect/io_uring denied; only Unix stream socketpair allowed", flush=True)
    if sys.argv[1:] == ["--self-check"]:
        return
    env = {key: value for key, value in os.environ.items()
           if key not in {"PYTEST_ADDOPTS", "PYTHONPATH", "PYTHONHOME", "PYTEST_PLUGINS"}}
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONDONTWRITEBYTECODE="1",
               OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    os.chdir(ROOT)
    python = ROOT / ".venv" / "bin" / "python"
    os.execve(python, [str(python), "-m", "pytest", "-p", "pytest_asyncio.plugin",
                       "-p", "pytest_socket", "-p", "pytest_timeout",
                       "-p", "pytest_homeassistant_custom_component.plugins",
                       "-p", "no:cacheprovider",
                       "-q", "-s", str(TEST_DIR)], env)


if __name__ == "__main__":
    main()