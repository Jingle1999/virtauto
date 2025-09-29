# Image Consistency Agent

This agent normalizes `<img>` tags across your HTML files.

## Features
- Adds `class="responsive-img"` if missing
- Adds `loading="lazy"` and `decoding="async"` (first image per page is `eager`)
- Strips inline width/height styles
- Optional: set intrinsic width/height via Pillow

## Usage
```bash
# Dry run
python tools/image_consistency_agent.py --root . --dry-run

# Apply changes
python tools/image_consistency_agent.py --root . --apply

# With intrinsic dimensions (needs Pillow)
pip install pillow beautifulsoup4
python tools/image_consistency_agent.py --root . --apply --set-dimensions
```
