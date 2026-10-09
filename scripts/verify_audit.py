"""M1 demo moment. Run: python -m scripts.verify_audit [path]"""
import sys
from pathlib import Path
from aegis.audit.chain import verify_chain, LOG
p = Path(sys.argv[1]) if len(sys.argv) > 1 else LOG
ok, bad = verify_chain(p)
print(f"{p}: {'CHAIN INTACT' if ok else f'TAMPERING DETECTED at line {bad}'} ({len(p.read_text().splitlines())} records)")
