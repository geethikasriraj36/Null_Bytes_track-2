"""Builds data/qgate_train.jsonl and data/qgate_test.jsonl from deepset/prompt-injections
(Apache-2.0, ~660 labelled rows) plus our own simulator docs. The TEST file is never used for training."""
import json, random
from pathlib import Path
from datasets import load_dataset          # pip install datasets

ds = load_dataset("deepset/prompt-injections")
def rows(split):
    return [{"text": r["text"], "label": int(r["label"])} for r in ds[split]]
# our clean docs as benign rows; demo_*.md is the poisoned demo doc and must never be labelled benign
own = [{"text": p.strip(), "label": 0} for f in Path("data/docs").glob("*.md") if not f.name.startswith("demo_")
       for p in f.read_text(encoding="utf-8").split("\n\n") if len(p.strip()) > 20 and "ai assistant" not in p.lower()]
train, test = rows("train") + own, rows("test")
random.Random(0).shuffle(train)
for name, data in [("qgate_train", train), ("qgate_test", test)]:
    Path(f"data/{name}.jsonl").write_text("\n".join(json.dumps(r) for r in data) + "\n")
    print(name, len(data), "rows,", sum(r["label"] for r in data), "injections")
