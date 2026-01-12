import re, json, os
from difflib import SequenceMatcher

BASE = os.path.dirname(os.path.dirname(__file__))
SYN = json.load(open(os.path.join(BASE, "data", "synonyms.json")))

def normalize(txt: str) -> str:
    return re.sub(r"[^a-z0-9\s]+", "", txt.lower()).strip()

def similarity(a,b):
    return SequenceMatcher(None, a,b).ratio()

def detect_category(text):
    t = normalize(text)
    for key, vals in SYN.items():
        if key in ("yes","no"): continue
        for v in vals + [key]:
            if v in t or similarity(t,v) > 0.7:
                return key
    return "unknown"

def detect_yes_no(text):
    t = normalize(text)
    for k in ("yes","no"):
        for v in SYN[k]+[k]:
            if v in t:
                return k
    return None