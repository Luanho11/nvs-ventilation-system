"""Lanzador (también usado por PyInstaller como script de entrada)."""
import sys

from nvs.app import main

if __name__ == "__main__":
    sys.exit(main())
