import hashlib
import os
import platform
import uuid
from pathlib import Path


OWNER_MACHINE_HASH = "e59045fd2afaa7fcd9a6f4cf8b26b277c7ff7e4dd88a92569f06b2a07a345609"


def get_machine_fingerprint():
    parts = [
        platform.system(),
        platform.node(),
        platform.machine(),
        str(uuid.getnode()),
        os.environ.get("USERNAME", ""),
    ]

    raw = "|".join(parts)

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def is_developer_machine():
    if not OWNER_MACHINE_HASH:
        return False

    return get_machine_fingerprint() == OWNER_MACHINE_HASH


def get_developer_fingerprint():
    return get_machine_fingerprint()