#used for deeper union of dictionaries 
from typing import Optional, Dict, List, Any, Annotated


def deep_union(left: Dict[str, Any] | None, right: Dict[str, Any] | None) -> Dict[str, Any]:
    left = left or {}
    right = right or {}

    out = dict(left)

    for key_, rvals in right.items():
        lvals = out.get(key_)

        if isinstance(lvals, dict) and isinstance(rvals, dict):
            out[key_] = {**lvals, **rvals} 
        else:
            out[key_] = rvals

    return out
