from django.core.cache import caches

wcache = lambda: caches["write_cache"]
rcache = lambda: caches["read_cache"]
