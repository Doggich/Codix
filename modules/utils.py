import os
import re


def is_safe_path(path):
    """Check path safety"""
    try:
        path = os.path.abspath(os.path.realpath(path))
        protected_patterns = [
            r"^/proc/", r"^/sys/", r"^/dev/", r"^/boot/",
            r"^/etc/", r"^/root/", r"^/var/log/"
        ]
        for pattern in protected_patterns:
            if re.match(pattern, path):
                return False
        if os.path.exists(path):
            if os.path.islink(path):
                return False
            if not (os.access(path, os.R_OK) and os.access(path, os.W_OK)):
                return False
        return True
    except Exception:
        return False