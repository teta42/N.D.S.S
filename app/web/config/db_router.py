import logging, sys
logger = logging.getLogger("myapp")

class MasterReplicaRouter:
    def db_for_read(self, model, **hints):
        if 'test' in sys.argv:
            return 'default'  # во время тестов читаем с default
        return 'replica'

    def db_for_write(self, model, **hints):
        logger.debug(f"WRITE to master")
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True  # разрешаем связи между всеми БД

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'default'  # миграции только на мастере

