class LMSDatabaseRouter:
    """
    A router to control all database operations on models in the
    lms application. Guarantees zero leakage between ERP and LMS databases.
    """
    route_app_labels = {'lms'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'lms'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'lms'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations only if both models reside in the same database app
        if (obj1._meta.app_label in self.route_app_labels and obj2._meta.app_label in self.route_app_labels) or \
           (obj1._meta.app_label not in self.route_app_labels and obj2._meta.app_label not in self.route_app_labels):
            return True
        return False

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'lms'
        return db == 'default'
