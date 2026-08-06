# Upgrading the existing GitHub repository

These files are designed to replace the current SQL-only prototype while preserving its history in `legacy/`.

## Recommended Git workflow

```bash
git clone https://github.com/bethmagembe/trading-system.git
cd trading-system
git checkout -b feature/platform-v2
```

Unzip the enhanced project somewhere else, then copy its contents into the cloned repository. On macOS:

```bash
rsync -av --exclude='.git' /path/to/trading-system-portfolio/ ./
```

Review the changes:

```bash
git status
git diff --stat
```

Create and activate the environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest
```

Commit and push:

```bash
git add .
git commit -m "Expand SQL prototype into multi-asset trading research platform"
git push -u origin feature/platform-v2
```

Open a pull request from `feature/platform-v2` into `main`, verify CI, then merge.
