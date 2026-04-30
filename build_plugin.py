#!/usr/bin/env python3
"""
Build script canonico per il plugin ShellExecAsUser.

CLI standard: vedi `python build_plugin.py --help`
"""
from __future__ import annotations

import argparse
import errno
import io
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Ensure UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
DIST_DIR = ROOT / "dist"
VERSION_FILE = ROOT / "VERSION"

# Mapping CLI config -> (MSBuild Configuration, MSBuild Platform, dist subdir)
CONFIGS = {
    "x86-ansi":     ("Release",         "Win32", "x86-ansi"),
    "x86-unicode":  ("Release Unicode", "Win32", "x86-unicode"),
    "x64-unicode":  ("Release Unicode", "x64",   "amd64-unicode"),
}

VCXPROJ = SRC_DIR / "ShellExecAsUser.vcxproj"
DLL_NAME = "ShellExecAsUser.dll"

_print_lock = threading.Lock()


# =============================================================================
# Utilities (copied verbatim from nsInnoUnp/build_plugin.py)
# =============================================================================

def _on_rmtree_error(func, path, exc_info):
    """Error handler for shutil.rmtree to handle read-only files and temporary locks on Windows."""
    if func in (os.unlink, os.rmdir) and exc_info[1].errno == errno.EACCES:
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
            return
        except Exception:
            pass
    for i in range(5):
        try:
            time.sleep(0.1 * (i + 1))
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.unlink(path)
            return
        except Exception:
            pass
    raise exc_info[1]


def robust_rmtree(path) -> None:
    """Robustly remove a directory tree, handling Windows file locking issues."""
    if not os.path.exists(path):
        return
    try:
        shutil.rmtree(path, onexc=_on_rmtree_error)
    except TypeError:
        try:
            shutil.rmtree(path, onerror=_on_rmtree_error)
        except Exception:
            pass
    except Exception:
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass


class Colors:
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    GRAY = "\033[90m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_RED = "\033[91m"


class Spinner:
    """A colored terminal spinner with elapsed time display."""
    def __init__(self, message: str = "Building...", delay: float = 0.1):
        self.spinner = ['\u280b', '\u2819', '\u2839', '\u2838', '\u283c', '\u2834', '\u2826', '\u2827', '\u2807', '\u280f']
        self.delay = delay
        self.message = message
        self.running = False
        self.thread = None
        self.start_time = time.time()

    def _spin(self):
        idx = 0
        while self.running:
            elapsed = time.time() - self.start_time
            time_blocks = f"{Colors.YELLOW}{'\u28ff' * int(elapsed // 2)}{Colors.RESET}"
            spin_char = f"{Colors.YELLOW}{self.spinner[idx % len(self.spinner)]}{Colors.RESET}"
            msg = f"{Colors.BOLD}{Colors.CYAN}{self.message}{Colors.RESET}"
            time_str = f"{Colors.GREEN}{int(elapsed)}s{Colors.RESET}"
            sys.stdout.write(f"\r{msg} {time_str} {time_blocks}{spin_char} ")
            sys.stdout.flush()
            idx += 1
            time.sleep(self.delay)
        sys.stdout.write("\r" + " " * (len(self.message) + 80) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        if sys.stdout.isatty():
            self.running = True
            self.start_time = time.time()
            self.thread = threading.Thread(target=self._spin, daemon=True)
            self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.2f}s"
    m = int(seconds // 60)
    s = seconds - m * 60
    if m < 60:
        return f"{m}m {s:.1f}s"
    h = m // 60
    m = m % 60
    return f"{h}h {m}m {int(s)}s"


# =============================================================================
# Build logic
# =============================================================================

def read_version() -> str:
    # utf-8-sig strips BOM (\ufeff) automatically
    return VERSION_FILE.read_text(encoding="utf-8-sig").strip()


_VS_VERSION_RANGE = {'2026': '[18.0,19.0)', '2022': '[17.0,18.0)'}
_VS_TOOLSET = {'2026': 'v145', '2022': 'v143'}
_VSWHERE = (
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
)


def find_msbuild(vs_version: str = 'auto') -> tuple[Path, str, str] | None:
    """Locate MSBuild via vswhere, returning (path, toolset, vs_year) or None."""
    if _VSWHERE.exists():
        versions_to_try = ['2022', '2026'] if vs_version == 'auto' else [vs_version]
        for ver in versions_to_try:
            if ver not in _VS_VERSION_RANGE:
                continue
            try:
                result = subprocess.run(
                    [str(_VSWHERE), '-version', _VS_VERSION_RANGE[ver], '-latest',
                     '-requires', 'Microsoft.Component.MSBuild',
                     '-find', r'MSBuild\**\Bin\MSBuild.exe'],
                    capture_output=True, text=True, timeout=15,
                )
                lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
                if lines:
                    p = Path(lines[0])
                    if p.exists():
                        return p, _VS_TOOLSET[ver], ver
            except Exception:
                pass
    # Fallback to well-known paths
    versions = ['2022', '2026'] if vs_version == 'auto' else [vs_version]
    for ver in versions:
        for ed in ('Community', 'Professional', 'Enterprise', 'BuildTools'):
            p = Path(f'C:/Program Files/Microsoft Visual Studio/{ver}/{ed}/MSBuild/Current/Bin/MSBuild.exe')
            if p.exists():
                return p, _VS_TOOLSET.get(ver, 'v143'), ver
    return None


def get_plugins_dir() -> Path | None:
    """Return workspace-level plugins/ dir (3 levels above src/modules/<plugin>/)."""
    p = ROOT.parent.parent.parent / 'plugins'
    return p if p.is_dir() else None


def clean_build() -> None:
    """Remove dist/ and all MSBuild output directories."""
    for d in [
        DIST_DIR,
        SRC_DIR / "Release",
        SRC_DIR / "Release Unicode",
        SRC_DIR / "x64",
        SRC_DIR / "Debug",
        ROOT / "obj",
    ]:
        if d.exists():
            robust_rmtree(d)


def build_one(msbuild: Path, msbuild_config: str, platform: str,
              jobs: int, verbose: bool, rebuild: bool) -> tuple[bool, float]:
    """Build one configuration, returning (success, elapsed_seconds)."""
    t0 = time.time()
    cmd = [
        str(msbuild), str(VCXPROJ),
        f"/p:Configuration={msbuild_config}",
        f"/p:Platform={platform}",
        f"/m:{jobs}",
        "/nologo",
        "/v:" + ("normal" if verbose else "minimal"),
    ]
    if rebuild:
        cmd.append("/t:Rebuild")
    result = subprocess.run(cmd, capture_output=not verbose)
    return result.returncode == 0, time.time() - t0


def collect_dll(msbuild_config: str, platform: str, dist_subdir: str) -> Path | None:
    """Find built DLL and copy to dist/<dist_subdir>/. Returns dest path or None."""
    plat_dir = "" if platform == "Win32" else platform + "/"
    candidates = list(SRC_DIR.glob(f"**/{plat_dir}{msbuild_config}/{DLL_NAME}"))
    candidates += list(ROOT.glob(f"**/{plat_dir}{msbuild_config}/{DLL_NAME}"))
    if not candidates:
        return None
    src = candidates[0]
    dst_dir = DIST_DIR / dist_subdir
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / DLL_NAME
    shutil.copy2(src, dst)
    return dst


def copy_to_plugins(dist_subdir: str, plugins_dir: Path) -> Path | None:
    """Copy DLL from dist/<dist_subdir>/ to plugins/<dist_subdir>/."""
    src = DIST_DIR / dist_subdir / DLL_NAME
    if not src.exists():
        return None
    dst_dir = plugins_dir / dist_subdir
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / DLL_NAME
    shutil.copy2(src, dst)
    return dst


def build_parallel(msbuild: Path, configs_to_build: list[str],
                   jobs: int, verbose: bool, rebuild: bool) -> list[tuple[str, bool, float]]:
    """Build all configs in parallel using ThreadPoolExecutor."""
    results: list[tuple[str, bool, float]] = []

    def _run(cfg_name: str) -> tuple[str, bool, float]:
        msbuild_config, platform, _ = CONFIGS[cfg_name]
        ok, elapsed = build_one(msbuild, msbuild_config, platform, jobs, verbose, rebuild)
        with _print_lock:
            icon = f"{Colors.BRIGHT_GREEN}\u2713{Colors.RESET}" if ok else f"{Colors.RED}\u2717{Colors.RESET}"
            print(f"  {icon} {cfg_name:<18} {format_time(elapsed)}")
        return cfg_name, ok, elapsed

    with ThreadPoolExecutor(max_workers=len(configs_to_build)) as executor:
        futures = {executor.submit(_run, cfg): cfg for cfg in configs_to_build}
        with Spinner(f"Building {len(configs_to_build)} config(s) in parallel..."):
            for future in as_completed(futures):
                results.append(future.result())
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ShellExecAsUser plugin")
    parser.add_argument("--config", default="all",
                        choices=list(CONFIGS.keys()) + ["all"])
    parser.add_argument("--toolset", default="auto", choices=["2022", "2026", "auto"])
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    parser.add_argument("--rebuild", action="store_true", default=True)
    parser.add_argument("--no-rebuild", action="store_false", dest="rebuild")
    parser.add_argument("--clean", action="store_true", default=True)
    parser.add_argument("--no-clean", action="store_false", dest="clean")
    parser.add_argument("--parallel", action="store_true", default=True)
    parser.add_argument("--no-parallel", action="store_false", dest="parallel")
    parser.add_argument("--final", action="store_true", default=False,
                        help="Force rebuild+clean, disable incremental build")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--version", action="store_true",
                        help="Mostra versione e termina")
    args = parser.parse_args()

    if args.version:
        print(read_version())
        return 0

    if args.final:
        args.rebuild = True
        args.clean = True

    if not VCXPROJ.exists():
        print(f"{Colors.RED}ERROR: {VCXPROJ} not found{Colors.RESET}", file=sys.stderr)
        return 2

    ver = read_version()
    print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}=== Building ShellExecAsUser v{ver} ==={Colors.RESET}")

    result = find_msbuild(args.toolset)
    if result is None:
        print(f"{Colors.RED}ERROR: MSBuild not found{Colors.RESET}", file=sys.stderr)
        return 2
    msbuild, toolset, vs_year = result
    print(f"{Colors.GRAY}[info]{Colors.RESET} MSBuild: {msbuild}")
    print(f"{Colors.GRAY}[info]{Colors.RESET} Toolset: {toolset} (VS {vs_year})")
    print(f"{Colors.GRAY}[info]{Colors.RESET} CPUs:    {args.jobs}")
    print("=" * 50)

    if args.clean:
        clean_build()

    configs_to_build = list(CONFIGS.keys()) if args.config == "all" else [args.config]
    wall_t0 = time.time()

    if args.parallel and len(configs_to_build) > 1:
        build_results = build_parallel(msbuild, configs_to_build, args.jobs, args.verbose, args.rebuild)
    else:
        build_results = []
        for cfg_name in configs_to_build:
            msbuild_config, platform, _ = CONFIGS[cfg_name]
            with Spinner(f"Building {cfg_name}..."):
                ok, elapsed = build_one(msbuild, msbuild_config, platform,
                                        args.jobs, args.verbose, args.rebuild)
            icon = f"{Colors.BRIGHT_GREEN}\u2713{Colors.RESET}" if ok else f"{Colors.RED}\u2717{Colors.RESET}"
            print(f"  {icon} {cfg_name:<18} {format_time(elapsed)}")
            build_results.append((cfg_name, ok, elapsed))

    wall_elapsed = time.time() - wall_t0
    print(f"\nAll {len(configs_to_build)} config(s) finished in {format_time(wall_elapsed)} (wall clock)")
    print("=" * 50)

    plugins_dir = get_plugins_dir()
    all_ok = True
    plugins_copied: list[str] = []
    for cfg_name, ok, _ in build_results:
        msbuild_config, platform, dist_subdir = CONFIGS[cfg_name]
        if ok:
            dst = collect_dll(msbuild_config, platform, dist_subdir)
            if dst:
                print(f"  {Colors.GRAY}-> dist/{dist_subdir}/{DLL_NAME}{Colors.RESET}")
                if plugins_dir:
                    copy_to_plugins(dist_subdir, plugins_dir)
                    plugins_copied.append(dist_subdir)
            else:
                print(f"  {Colors.YELLOW}! {cfg_name}: DLL not found after build{Colors.RESET}")
                all_ok = False
        else:
            all_ok = False

    if plugins_copied:
        print(f"  {Colors.GRAY}-> plugins/{{{', '.join(plugins_copied)}}}/{Colors.RESET}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

    targets = list(CONFIGS.keys()) if args.config == "all" else [args.config]
    failed = []
    for cfg_name in targets:
        config, platform, subdir = CONFIGS[cfg_name]
        if not build_one(msbuild, config, platform, args.jobs, args.verbose):
            failed.append(cfg_name)
            continue
        dst = collect_dll(config, platform, subdir)
        if dst is None:
            print(f"ERROR: DLL not found for {cfg_name}", file=sys.stderr)
            failed.append(cfg_name)
        else:
            print(f"[ok] {dst}")
            if args.install_dir:
                install_path = args.install_dir / subdir
                install_path.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, install_path / DLL_NAME)
                print(f"[install] {install_path / DLL_NAME}")

    if failed:
        print(f"FAILED: {failed}", file=sys.stderr)
        return 1
    print("[done] all targets built successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
