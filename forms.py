from flask_wtf import Form  
from wtforms import StringField, PasswordField, BooleanField 
from wtforms.validators import DataRequired


class LoginForm(Form):  
    """Login form"""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

