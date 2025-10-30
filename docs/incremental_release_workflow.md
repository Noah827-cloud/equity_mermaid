# Incremental Release Workflow

This document captures the companion build pipeline that keeps the existing packaging flow intact while introducing an incremental-friendly layout.

## 1. Full incremental build

```
build_exe_incremental.bat
```

Steps performed:

- Validates the Anaconda Python interpreter path.
- Mirrors the helper scripts (`sync_utils_to_spec.py`, `check_all.py`) if present.
- Ensures PyInstaller is available (installs or upgrades when missing).
- Calls `equity_mermaid_incremental.spec` to produce `dist\equity_mermaid_tool_incremental\` where
  - `runtime\` hosts Python DLLs and other rarely changing binaries.
  - `app\` contains Python modules, Streamlit assets, and config files that we want to patch in-place.
- Runs `fix_protobuf_issue.py` at the end to keep parity with the classic build process.
- Invokes `scripts\verify_package_content.py dist\equity_mermaid_tool_incremental` for a quick sanity check.
- Captures a runtime/bootloader snapshot via `scripts\runtime_bootloader_guard.py`; if drift is detected a warning is printed and incremental patches are blocked until a full installer ships.

## 2. Create a patch package

```
build_exe_incremental.bat patch [version_label]
```

What happens:

- Optionally writes the supplied `version_label` into `dist\equity_mermaid_tool_incremental\app\version.txt`.
- Copies the entire `app\` tree into a timestamped staging folder under `dist\patches\`.
- Compresses the staged `app\` directory so the archive keeps the `app\` top-level folder.
- Drops `scripts\apply_incremental_patch.bat` alongside the zip for distribution.
- Aborts immediately when the runtime/bootloader guard flag is present (meaning a full installer is required).

Example output directory:

```
dist\
  equity_mermaid_tool_incremental\
    app\...
    runtime\...
  patches\
    equity_mermaid_patch_20250315_223045\
      equity_mermaid_patch_20250315_223045.zip
      apply_incremental_patch.bat
```

## 3. Apply the patch on a target machine (no Python required)

Ship the archive and the helper script to the machine that already has the app installed. Place both files next to the installation root (the folder that contains `app\`, `runtime\`, and the executable), then run:

```
apply_incremental_patch.bat equity_mermaid_patch_20250315_223045.zip
```

The script:

1. Extracts the archive to a temporary folder.
2. Mirrors the `app\` payload over the existing installation (using `robocopy`).
3. Shows the new version number when `app\version.txt` is present.

You can also pass the install directory explicitly as the second argument if the script lives elsewhere.

## 4. Notes and next steps

- The original `build_exe.bat` and `equity_mermaid.spec` stay untouched, so you can continue to publish the legacy bundle when needed.
- The incremental layout is only useful if future changes stay within the `app\` directory. DLL/EXE changes still require a full rebuild.
- Consider adding a smoke test that runs against `dist\equity_mermaid_tool_incremental\` so regressions are caught before patch creation.
