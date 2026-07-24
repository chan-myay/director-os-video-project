from __future__ import annotations

import subprocess


def installed_burmese_fonts() -> dict:
    try:
        result = subprocess.run(["fc-list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8, check=False)
        text = result.stdout
    except Exception:
        text = ""
    names = []
    for line in text.splitlines():
        if any(token.lower() in line.lower() for token in ["myanmar", "burmese", "noto sans myanmar", "padauk"]):
            names.append(line.split(":")[0])
    return {"available": bool(names), "fonts": sorted(set(names))[:50], "font_files_not_redistributed": True}
