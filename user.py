from werkzeug.security import check_password_hash

class User():

    def __init__(self, username, groups, role):
        self.username = username
        self.groups = groups
        self.role = role

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username

    def get_groups(self):
        return self.groups

    def get_role(self):
        return self.role
    
    
    @staticmethod
    def validate_login(password_hash, password):
        return check_password_hash(password_hash, password)
