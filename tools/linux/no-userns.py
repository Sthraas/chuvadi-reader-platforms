#!/usr/bin/python3
"""Runs a command where new user namespaces are refused (test-only, never shipped) — what Docker's default
seccomp profile, a hardened kernel, or Ubuntu 24.04+ without the AppArmor profile do to WebKit's sandbox.

  tools/linux/no-userns.py <command> [args...]

clone / unshare with CLONE_NEWUSER fail with EPERM; clone3 reports ENOSYS so callers fall back to clone
(as Docker does). Needs python3-seccomp (Ubuntu's binding is built for the system Python, /usr/bin/python3).
"""
import errno, os, sys

import seccomp

CLONE_NEWUSER = 0x10000000
f = seccomp.SyscallFilter(defaction=seccomp.ALLOW)
f.add_rule(seccomp.ERRNO(errno.EPERM), "unshare", seccomp.Arg(0, seccomp.MASKED_EQ, CLONE_NEWUSER, CLONE_NEWUSER))
f.add_rule(seccomp.ERRNO(errno.EPERM), "clone", seccomp.Arg(0, seccomp.MASKED_EQ, CLONE_NEWUSER, CLONE_NEWUSER))
f.add_rule(seccomp.ERRNO(errno.ENOSYS), "clone3")
f.load()
os.execvp(sys.argv[1], sys.argv[1:])
