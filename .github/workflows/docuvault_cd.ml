name: DocuVault CD

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flake8 pytest
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
      - name: Lint with flake8
        run: |
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
      - name: Test with pytest
        run: |
          pytest

  build:
    needs: test
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyinstaller pillow pycryptodome schedule requests
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
      - name: Build with PyInstaller
        run: |
          pyinstaller --onefile --windowed --icon=AppIcon/DocuVault-icon.ico --add-data "AppIcon;AppIcon" main.py
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: docuvault-executable
          path: dist/

  release:
    needs: build
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Download artifact
        uses: actions/download-artifact@v3
        with:
          name: docuvault-executable
          path: dist/
      - name: Create Release
        id: create_release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            dist/main.exe
          tag_name: v${{ github.run_number }}
          name: DocuVault Release v${{ github.run_number }}
          draft: false
          prerelease: false
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

