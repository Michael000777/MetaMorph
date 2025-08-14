#used for deeper union of dictionaries 

def deep_union(left, right):
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
