def get_key(s, k, default = None):
    try:
        return s.get(k, default)
    except AttributeError:
        return default
    

def get_attr_or_item(object, key, default = None):
    if object is None:
        return default
    if hasattr(object, "model_dump"):
        try:
            return object.model_dump().get(key, default)
        except Exception:
            pass
    
    if isinstance(object, dict):
        return object.get(key, default)
    
    return getattr(object, key, default)


def normalize_to_colmatrix(values):
    if values is None:
        return []
    if not isinstance(values, (list, tuple)):
        return [[values]]
    
    if len(values) == 0:
        return []
    
    if all(isinstance(v, (list, tuple)) for v in values):
        return [list(col) for col in values]
    

    return [list(values)]