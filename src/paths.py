"""Repository paths. Everything is relative to the repo root, so the pipeline runs anywhere."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
RESULTS = os.path.join(ROOT, 'results')
CACHE = os.path.join(ROOT, '.cache')
PUBLIC = os.path.join(ROOT, 'public')
for _p in (DATA, RESULTS, CACHE, PUBLIC):
    os.makedirs(_p, exist_ok=True)
