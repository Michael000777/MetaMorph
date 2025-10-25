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