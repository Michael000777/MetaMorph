import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.MetaMorphState import ColSample, MetaMorphState


def transform_to_native_list(seq):

#Purpose of function is to avoid LLM and serialization problems down the line.

    native = []
    for x in seq:
        if hasattr(x, "item"):
            native.append(x.item())

        elif hasattr(x, "isoformat"):
            native.append(x.isoformat())

        elif x is None or isinstance(x, (str, int, float, bool)):
            native.append(x)

        else:
            native.append(str(x))
    
    return native


def build_sample_data(s, *, n_head=10, n_tail=10, n_rand=25, n_unique=50, rand_seed=0) -> ColSample:

    num = int(len(s))
    head = transform_to_native_list(s.head(n_head).tolist())
    tail = transform_to_native_list(s.tail(n_tail).tolist())

    _k = min(n_rand, max(num - (n_head + n_tail), 0)) #random sampling but avoiding dupliating or overlapping head/tail for short cols

    rand = transform_to_native_list(s.sample(_k, random_state=rand_seed).tolist())

    #Now implementing unique preview for inference node 
    unique_values = s.dropna().astype(str).unique()[:n_unique]
    unique_values = transform_to_native_list(list(unique_values))

    return ColSample(
        column_name=str(getattr(s, "name", "unknown") or "unknown"),
        head=head,
        tail=tail,
        random_sample=rand,
        n_unique_preview=int(s.nunique(dropna=True)),
        unique_preview=unique_values,
        row_count = num,
    )

#Now populating State 