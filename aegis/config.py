"""Which layers are on. Ablation configs in configs/*.yaml override these."""
import os, yaml
from pathlib import Path
DEFAULT = {"J": True, "LINE1": True, "QGATE": True, "CLASSICAL": False,
           "D": True, "T": True, "H": True, "M": True}
CFG = dict(DEFAULT)

def use(path_or_dict):
    """Switch config at runtime (the eval runner calls this per config)."""
    CFG.clear(); CFG.update(DEFAULT)
    CFG.update(path_or_dict if isinstance(path_or_dict, dict) else yaml.safe_load(Path(path_or_dict).read_text()))

if os.environ.get("AEGIS_CONFIG"):
    use(os.environ["AEGIS_CONFIG"])
