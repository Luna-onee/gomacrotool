"""
Build script for Jaide's Macro Tool.
Hashes all source files, compares with last build, and rebuilds the exe if anything changed.

Usage:
    python build.py          # Build only if sources changed
    python build.py --force  # Force rebuild regardless
    python build.py --hash   # Just show current hashes, don't build
    python build.py --check  # Validate all source files without building
"""
import sys
import os
import hashlib
import json
import subprocess
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
HASH_FILE = os.path.join(ROOT, ".build_hashes")
EXE_NAME = "Jaide's Macro Tool"

WATCHED_EXTENSIONS = {".py", ".c", ".kdl", ".txt"}

WATCHED_FILES = [
    "main.py",
    "setup.py",
    "native_module.c",
    "config.kdl",
    "requirements.txt",
    "modules/__init__.py",
    "modules/config_manager.py",
    "modules/game_detection.py",
    "modules/overlay.py",
    "modules/macro_engine.py",
    "modules/pixel_triggers.py",
    "modules/input_handler.py",
    "modules/buff_engine.py",
    "modules/utils.py",
    "modules/theme.py",
    "modules/debug_server.py",
    "modules/pixel_picker.py",
    "modules/gui/__init__.py",
    "modules/gui/main_window.py",
    "modules/gui/material_style.py",
    "modules/gui/macro_editor.py",
    "modules/gui/pixel_editor.py",
    "modules/gui/buff_editor.py",
    "modules/gui/spec_detect_editor.py",
]


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_hashes():
    hashes = {}
    for rel in WATCHED_FILES:
        full = os.path.join(ROOT, rel)
        if os.path.exists(full):
            hashes[rel] = file_hash(full)
    return hashes


def load_saved_hashes():
    if not os.path.exists(HASH_FILE):
        return None
    try:
        with open(HASH_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_hashes(hashes):
    with open(HASH_FILE, "w") as f:
        json.dump(hashes, f, indent=2)


def hashes_changed(current, saved):
    if saved is None:
        return True, list(current.keys())
    changed = []
    for rel, h in current.items():
        if rel not in saved or saved[rel] != h:
            changed.append(rel)
    for rel in saved:
        if rel not in current:
            changed.append(rel)
    return bool(changed), changed


def validate_sources():
    """Check all Python files for syntax errors without importing them."""
    import py_compile
    errors = []
    for rel in WATCHED_FILES:
        if not rel.endswith(".py"):
            continue
        full = os.path.join(ROOT, rel)
        if not os.path.exists(full):
            errors.append(f"  MISSING: {rel}")
            continue
        try:
            py_compile.compile(full, doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"  SYNTAX ERROR in {rel}: {e}")
    if errors:
        print("[check] Validation FAILED:")
        for e in errors:
            print(e)
        return False
    print("[check] All source files valid.")
    return True


def build_native():
    print("[build] Compiling native extension...")
    result = subprocess.run(
        [sys.executable, "setup.py", "build_ext", "--inplace"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        print("[build] FAILED: native extension compilation error")
        sys.exit(1)
    print("[build] Native extension compiled.")


def _unlock_exe(exe_path):
    """Try to rename or remove a locked exe so PyInstaller can overwrite it."""
    if not os.path.exists(exe_path):
        return True
    # Try renaming to .old
    old_path = exe_path + ".old"
    if os.path.exists(old_path):
        try:
            os.remove(old_path)
        except OSError:
            pass
    try:
        os.rename(exe_path, old_path)
        print(f"[build] Renamed locked exe to {os.path.basename(old_path)}")
        return True
    except OSError:
        pass
    return False


def build_exe():
    dist_dir = os.path.join(ROOT, "dist")
    build_dir = os.path.join(ROOT, "build_pyinstaller")

    native_pyd = os.path.join(ROOT, "_native.pyd")
    if not os.path.exists(native_pyd):
        print("[build] _native.pyd not found, compiling...")
        build_native()

    icon_file = os.path.join(ROOT, "icon.ico")
    icon_arg = f'icon={repr(icon_file)},' if os.path.exists(icon_file) else ''

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
import os
icon_file = {repr(icon_file)}
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('_native.pyd', '.'),
        ('icon.ico', '.'),
        ('modules/gui/__qss_cache', 'modules/gui/__qss_cache'),
    ],
    hiddenimports=['ckdl'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name={repr(EXE_NAME)},
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {icon_arg}
)
"""
    spec_path = os.path.join(ROOT, "build.spec")
    with open(spec_path, "w") as f:
        f.write(spec_content)

    # Validate spec syntax before running PyInstaller
    try:
        compile(spec_content, spec_path, "exec")
    except SyntaxError as e:
        print(f"[build] FAILED: Generated spec has syntax error: {e}")
        sys.exit(1)

    # Check for locked exe
    exe_path = os.path.join(dist_dir, f"{EXE_NAME}.exe")
    if os.path.exists(exe_path):
        if not _unlock_exe(exe_path):
            print(f"[build] FAILED: {EXE_NAME}.exe is running/locked.")
            print("[build] Please close the application and try again.")
            sys.exit(1)

    spec_args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath", dist_dir,
        "--workpath", build_dir,
        spec_path,
    ]

    print(f"[build] Building '{EXE_NAME}.exe' with PyInstaller...")
    result = subprocess.run(spec_args, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        print("[build] FAILED: PyInstaller error")
        sys.exit(1)

    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"[build] Success: {exe_path} ({size_mb:.1f} MB)")
    else:
        print("[build] FAILED: exe not found in dist/")
        sys.exit(1)


def main():
    force = "--force" in sys.argv
    show_hash = "--hash" in sys.argv
    check_only = "--check" in sys.argv

    os.chdir(ROOT)

    if check_only:
        validate_sources()
        return

    current = compute_hashes()

    if show_hash:
        saved = load_saved_hashes()
        for rel, h in sorted(current.items()):
            status = " " if saved and saved.get(rel) == h else "*"
            print(f" {status} {rel}: {h[:16]}...")
        if saved:
            changed, files = hashes_changed(current, saved)
            if changed:
                print(f"\n Changed: {', '.join(files)}")
            else:
                print("\n No changes.")
        else:
            print("\n No previous build hashes found.")
        return

    changed, files = hashes_changed(current, load_saved_hashes())

    if not changed and not force:
        print("[build] No source changes detected. Use --force to rebuild anyway.")
        return

    if changed:
        print(f"[build] Changed files: {', '.join(files)}")

    # Pre-build validation
    if not validate_sources():
        print("[build] Aborting due to validation errors.")
        sys.exit(1)

    build_exe()

    save_hashes(compute_hashes())
    print("[build] Hashes saved.")


if __name__ == "__main__":
    main()
