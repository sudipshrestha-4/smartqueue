import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp, ValidationError
from email_validator import validate_email, EmailNotValidError


def validate_real_email(form, field):
    """Rejects made-up/non-existent domains by checking the domain actually has
    mail servers (MX records) — catches typos and fake domains, not just bad syntax."""
    try:
        validate_email(field.data, check_deliverability=True)
    except EmailNotValidError as e:
        raise ValidationError(str(e))


def validate_strong_password(form, field):
    password = field.data
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter.')
    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter.')
    if not re.search(r'\d', password):
        raise ValidationError('Password must contain at least one number.')
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=]', password):
        raise ValidationError('Password must contain at least one special character (e.g. ! @ # $).')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])

    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Enter a valid email address.'),
        validate_real_email
    ])

    phone = StringField('Phone Number', validators=[
        DataRequired(),
        Regexp(r'^\d{10}$', message='Phone number must be exactly 10 digits (numbers only).')
    ])

    password = PasswordField('Password', validators=[
        DataRequired(),
        validate_strong_password
    ])

    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match.')]
    )

    submit = SubmitField('Register')
class StaffForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])

    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Enter a valid email address.'),
        validate_real_email
    ])

    phone = StringField('Phone Number', validators=[
        DataRequired(),
        Regexp(r'^\d{10}$', message='Phone number must be exactly 10 digits (numbers only).')
    ])

    password = PasswordField('Password', validators=[
        DataRequired(),
        validate_strong_password
    ])

    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match.')]
    )

    submit = SubmitField('Create Staff Account')