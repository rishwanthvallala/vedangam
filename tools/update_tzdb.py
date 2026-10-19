#!/usr/bin/env python3
"""Refresh app/data/tzdb.zip, the time-zone database the engine uses.

The engine does not use the operating system's zone files. macOS and the PyPI `tzdata`
package merge zones whose clocks agree since 1970 (Oslo into Berlin, Amsterdam into
Brussels, …), which gives wrong offsets for older births; Debian and Ubuntu keep every
zone's own history (IANA "backzone"). Bundling one copy makes every machine, and the
in-browser engine, resolve historical times identically.

Source: Debian's tzdata package. Only its data files are read; nothing in it is run.
Usage:  .venv/bin/python tools/update_tzdb.py 2026e-1
"""
from __future__ import annotations

import io
import json
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "data" / "tzdb.zip"
POOL = "https://deb.debian.org/debian/pool/main/t/tzdata/"
PREFIX = "./usr/share/zoneinfo/"
SKIP = ("posix/", "right/", "localtime", "posixrules")


def ar_members(blob: bytes):
    """Members of a Unix ar archive (the outer format of a .deb)."""
    assert blob[:8] == b"!<arch>\n", "not a .deb"
    pos = 8
    while pos < len(blob):
        head = blob[pos:pos + 60]
        name, size = head[:16].decode().strip().rstrip("/"), int(head[48:58])
        yield name, blob[pos + 60:pos + 60 + size]
        pos += 60 + size + (size & 1)


def main(version: str):
    url = f"{POOL}tzdata_{version}_all.deb"
    print(f"downloading {url}")
    deb = urllib.request.urlopen(url).read()
    data = next(b for n, b in ar_members(deb) if n.startswith("data.tar"))
    zones, links, zi = {}, {}, ""
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for m in tar.getmembers():
            if not m.name.startswith(PREFIX):
                continue
            name = m.name[len(PREFIX):]
            if name.startswith(SKIP):
                continue
            if m.isfile():
                blob = tar.extractfile(m).read()
                if blob[:4] == b"TZif":
                    zones[name] = blob
                elif name == "tzdata.zi":
                    zi = blob.decode()
            elif m.issym() or m.islnk():
                target = m.linkname
                if m.issym():   # relative to the link's own directory
                    target = str(Path(name).parent / target)
                    target = str(Path("/" + target).resolve())[1:]
                else:
                    target = target[len(PREFIX):] if target.startswith(PREFIX) else target
                links[name] = target
    for line in zi.splitlines():      # backward-compatible names (Asia/Calcutta, US/Eastern, …)
        if line.startswith("L "):
            _, target, name = line.split()
            links.setdefault(name, target)
    links = {k: v for k, v in sorted(links.items()) if v in zones and k not in zones}
    zi_version = next((ln.split()[-1] for ln in zi.splitlines() if ln.startswith("# version")), version)

    stamp = (2000, 1, 1, 0, 0, 0)          # fixed timestamps keep the archive reproducible
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        def put(name, blob):
            z.writestr(zipfile.ZipInfo(name, stamp), blob, compress_type=zipfile.ZIP_DEFLATED)
        put("VERSION", f"{zi_version} (Debian tzdata {version})\n")
        put("links.json", json.dumps(links, indent=0))
        for name in sorted(zones):
            put(name, zones[name])
    print(f"wrote {OUT.relative_to(ROOT)}: tzdb {zi_version}, {len(zones)} zones, {len(links)} aliases, "
          f"{OUT.stat().st_size / 1e3:.0f} kB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
