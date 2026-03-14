"""
Build and packaging script for USD/BDT Trading Bot
Converts Python application to Windows executable using PyInstaller
"""

import PyInstaller.__main__
import os
from pathlib import Path
import shutil

PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"


def build_executable():
    """Build Windows executable using PyInstaller"""
    
    print("=" * 60)
    print("USD/BDT Trading Bot - Build Script")
    print("=" * 60)
    
    # Clean previous builds
    print("\n[1/4] Cleaning previous builds...")
    for dir_path in [DIST_DIR, BUILD_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  Removed {dir_path}")
    
    # PyInstaller arguments
    print("\n[2/4] Configuring PyInstaller...")
    
    main_script = str(SRC_DIR / "main_app.py")
    
    pyinstaller_args = [
        main_script,
        "--name=QutexBot",
        "--onefile",
        "--windowed",
        "--icon=qutexbot.ico",  # Optional: add an icon file
        "--add-data",
        f"{SRC_DIR}/config.py;src",
        "--hidden-import=tensorflow",
        "--hidden-import=sklearn",
        "--hidden-import=numpy",
        "--hidden-import=pandas",
        "--hidden-import=PySimpleGUI",
        "--collect-all=tensorflow",
        "--collect-all=sklearn",
        "--distpath",
        str(DIST_DIR),
        "--buildpath",
        str(BUILD_DIR),
        "--specpath",
        str(PROJECT_ROOT),
        "--noconfirm",
    ]
    
    print("\n[3/4] Building executable...")
    print("  This may take 2-5 minutes...")
    
    try:
        PyInstaller.__main__.run(pyinstaller_args)
        print("  ✓ Build completed successfully!")
    except Exception as e:
        print(f"  ✗ Build failed: {e}")
        return False
    
    # Post-build steps
    print("\n[4/4] Post-build configuration...")
    
    # Check if executable was created
    exe_path = DIST_DIR / "QutexBot.exe"
    if exe_path.exists():
        print(f"  ✓ Executable created: {exe_path}")
        print(f"  ✓ Size: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
    else:
        print("  ✗ Executable not found!")
        return False
    
    # Copy additional files
    print("\n[5/5] Copying additional files...")
    
    # Copy requirements and readme
    files_to_copy = [
        ("requirements.txt", "requirements.txt"),
        ("README.md", "README.md"),
    ]
    
    for src_file, dst_file in files_to_copy:
        src_path = PROJECT_ROOT / src_file
        dst_path = DIST_DIR / dst_file
        if src_path.exists():
            shutil.copy2(src_path, dst_path)
            print(f"  ✓ Copied {dst_file}")
    
    print("\n" + "=" * 60)
    print("BUILD COMPLETE!")
    print("=" * 60)
    print(f"\nExecutable location: {exe_path}")
    print("\nNext steps:")
    print("1. Run: QutexBot.exe")
    print("2. Log in (any username/password in demo mode)")
    print("3. Click 'Train Model' to train on historical data")
    print("4. Click 'START' to begin trading")
    print("\nFor distribution:")
    print(f"- All files in '{DIST_DIR}' can be zipped and distributed")
    print("- Users will need Python installed for first-time setup")
    
    return True


def create_installer():
    """Create Windows installer (optional - requires NSIS)"""
    
    print("\n" + "=" * 60)
    print("Creating Windows Installer (NSIS)")
    print("=" * 60)
    
    # This would require NSIS to be installed
    # Placeholder for future implementation
    print("Installer creation requires NSIS to be installed")
    print("Download from: https://nsis.sourceforge.io/")


if __name__ == "__main__":
    import sys
    
    # Check for required packages
    try:
        import PyInstaller
        print("✓ PyInstaller found")
    except ImportError:
        print("✗ PyInstaller not found. Installing...")
        os.system("pip install pyinstaller")
    
    # Build executable
    success = build_executable()
    
    if success:
        print("\n✓ Build successful!")
        sys.exit(0)
    else:
        print("\n✗ Build failed!")
        sys.exit(1)
