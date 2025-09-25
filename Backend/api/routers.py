# # Backend/api/routers.py
# class MongoDBRouter:
#     """
#     A router to control all database operations on models in the api application
#     """
#     def db_for_read(self, model, **hints):
#         if model._meta.app_label == 'api':
#             return 'default'
#         return 'sqlite'

#     def db_for_write(self, model, **hints):
#         if model._meta.app_label == 'api':
#             return 'default'
#         return 'sqlite'

#     def allow_relation(self, obj1, obj2, **hints):
#         if obj1._meta.app_label == 'api' or obj2._meta.app_label == 'api':
#             return True
#         return None

#     def allow_migrate(self, db, app_label, model_name=None, **hints):
#         if app_label == 'api':
#             return db == 'default'
#         return db == 'sqlite'


# Backend/api/routers.py

class MongoDBRouter:
    """
    Route our app models to MongoDB (default), and let Django internals use SQLite.
    We also turned off migrations for the api app in settings.py,
    so Django won't try to create Mongo DDL via Djongo.
    """

    def db_for_read(self, model, **hints):
        # All api app reads go to Mongo
        if model._meta.app_label == "api":
            return "default"
        # Everything else (core apps) use SQLite
        return "sqlite"

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "api":
            return "default"
        return "sqlite"

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == "api" or obj2._meta.app_label == "api":
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # No migrations for api (we disabled them in settings anyway).
        if app_label == "api":
            return False
        # Core apps migrate only on SQLite.
        return db=="sqlite"