import mimetypes
import hashlib
import time
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


def print_file_info(filepath):
    print(f"\n--- File information: {filepath} ---")
    abs_path = os.path.abspath(filepath)
    print(f"\033[1;1m\033[1;3mAbsolute path\033[0m: {abs_path}")
    print(f"\033[1;1m\033[1;3mIs file\033[0m: {os.path.isfile(filepath)}")
    print(f"\033[1;1m\033[1;3mIs directory\033[0m: {os.path.isdir(filepath)}")
    if not os.path.isfile(filepath):
        return

    size = os.path.getsize(filepath)
    print(f"\033[1;1m\033[1;3mFile size\033[0m: {size} bytes")
    stat = os.stat(filepath)
    print("\033[1;1m\033[1;3mCreation time\033[0m:", time.ctime(stat.st_ctime))
    print("\033[1;1m\033[1;3mLast modified\033[0m:", time.ctime(stat.st_mtime))
    print("\033[1;1m\033[1;3mLast accessed\033[0m: ", time.ctime(stat.st_atime))
    print(f"\033[1;1m\033[1;3mPermissions\033[0m: {oct(stat.st_mode)[-3:]}")

    mime_type, encoding = mimetypes.guess_type(filepath)
    print(f"\033[1;1m\033[1;3mMIME type\033[0m: {mime_type}")
    print(f"\033[1;1m\033[1;3mMIME encoding\033[0m: {encoding}")

    try:
        import chardet
        with open(filepath, "rb") as f:
            raw = f.read(100000)
            detected = chardet.detect(raw)
        print(f"Detected encoding (chardet): {detected['encoding']} (confidence: {detected['confidence']:.2f})")
    except ImportError:
        print("Please install the `chardet` package for automatic encoding detection.")

    # Content statistics (for text files)
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        lines = content.count('\n') + 1 if content else 0
        words = len(content.split()) if content else 0
        chars = len(content)
        print(f"\033[1;1m\033[1;3mLines\033[0m: {lines}")
        print(f"\033[1;1m\033[1;3mWords\033[0m: {words}")
        print(f"\033[1;1m\033[1;3mCharacters\033[0m: {chars}")
    except Exception as e:
        print(f"Error reading file content: {e}")

    # MD5 hash
    try:
        with open(filepath, "rb") as f:
            h = hashlib.md5()
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        print(f"\033[1;1m\033[1;3mMD5 hash\033[0m: {h.hexdigest()}")
    except Exception as e:
        print(f"Error computing MD5: {e}")

    print("\n")
