from uuid import uuid5, NAMESPACE_DNS

def generate_thread_id(username):
    return str(uuid5(NAMESPACE_DNS, username.strip().lower()))
