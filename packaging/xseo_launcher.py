"""PyInstaller entry point. PyInstaller bundles a script, not a module
entry point, so this thin wrapper hands off to the real app."""

from xseo.ui.app import main

if __name__ == "__main__":
    main()
