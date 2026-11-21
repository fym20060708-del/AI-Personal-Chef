"""Build from a working Windows Python environment, without network access."""
import importlib.metadata as metadata
from pathlib import Path
import shutil
import sys

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
SOURCE_APP = ROOT / "app" if (ROOT / "app" / "main.py").exists() else ROOT


def dependencies():
    pending = [Requirement(line) for line in
               (ROOT / "requirements-runtime.txt").read_text().splitlines()
               if line and not line.startswith("#")]
    seen = set()
    distributions = {}
    while pending:
        req = pending.pop()
        name = canonicalize_name(req.name)
        dist = metadata.distribution(name)
        if req.specifier and not req.specifier.contains(dist.version):
            raise RuntimeError(f"Dependency version mismatch: {req}")
        distributions[name] = dist
        for extra in {"", *req.extras}:
            if (name, extra) in seen:
                continue
            seen.add((name, extra))
            for entry in dist.requires or []:
                child = Requirement(entry)
                if child.marker is None or child.marker.evaluate({"extra": extra}):
                    pending.append(child)
    return distributions


def main():
    if sys.platform != "win32" or sys.maxsize <= 2**32:
        raise RuntimeError("Build with 64-bit Windows Python")
    distributions = dependencies()
    destination = ROOT / "dist" / "AI-私人厨师-Windows"
    if destination.exists():
        raise RuntimeError(f"Output already exists; move it away first: {destination}")
    runtime = destination / "runtime"
    base = Path(sys.base_prefix)
    runtime.mkdir(parents=True)
    for path in base.iterdir():
        if path.is_file() and (path.suffix in {".exe", ".dll"} or path.name == "LICENSE.txt"):
            shutil.copy2(path, runtime / path.name)
    for folder in ("Lib", "DLLs"):
        shutil.copytree(base / folder, runtime / folder,
                        ignore=shutil.ignore_patterns("site-packages", "__pycache__", "test", "tests"))
    site = runtime / "Lib" / "site-packages"
    site.mkdir()
    for name, dist in sorted(distributions.items()):
        source = Path(dist.locate_file("")).resolve()
        for entry in dist.files or []:
            file = Path(dist.locate_file(entry)).resolve()
            if not file.is_relative_to(source) or not file.is_file() or "__pycache__" in file.parts:
                continue
            target = site / file.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target)
    application = destination / "app"
    application.mkdir()
    for folder in ("agents", "api", "common", "models", "static"):
        shutil.copytree(SOURCE_APP / folder, application / folder,
                        ignore=shutil.ignore_patterns("__pycache__"))
    for filename in ("__init__.py", "main.py"):
        shutil.copy2(SOURCE_APP / filename, application / filename)
    (destination / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts" / "launch.py", destination / "scripts" / "launch.py")
    for filename in ("启动网页.cmd", ".env.example", "README.md", "requirements-runtime.txt"):
        shutil.copy2(ROOT / filename, destination / filename)
    (destination / "data").mkdir()
    (destination / "DEPENDENCIES.txt").write_text(
        "\n".join(f"{name}=={dist.version}" for name, dist in sorted(distributions.items())),
        encoding="utf-8")
    archive = shutil.make_archive(str(destination), "zip", destination.parent, destination.name)
    print(f"Built {len(distributions)} distributions: {archive}")


if __name__ == "__main__":
    main()
