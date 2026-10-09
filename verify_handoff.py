"""Verify extracted handoff bytes against its manifest (standard library only)."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'MANIFEST_SHA256.json').read_text(encoding='utf-8'))
errors = []
for item in manifest['files']:
    path = (root / item['path']).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        errors.append(item['path'] + ': missing/unsafe')
        continue
    if path.stat().st_size != item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        errors.append(item['path'] + ': changed')
if errors:
    raise SystemExit('\n'.join(errors))
print(f"OK: {len(manifest['files'])} files verified. This validates package integrity, not strategy profitability.")
