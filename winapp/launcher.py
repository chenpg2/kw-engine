"""PyInstaller entry point — imports the package properly so relative imports work."""

import sys

from kwengine_app.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
