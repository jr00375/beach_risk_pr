def s3_uri(base: str, key: str) -> str:
    return base.rstrip('/') + '/' + key.lstrip('/')
