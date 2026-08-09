import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from email_validator import validate_email, EmailNotValidError


def validate_nepal_phone(form, field):
    """Nepal mobile: exactly 10 digits starting with 97 or 98."""
    phone = (field.data or '').strip()
    if not re.fullmatch(r'(97|98)\d{8}', phone):
        raise ValidationError('Phone number must be 10 digits and start with 97 or 98.')


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
        validate_nepal_phone,
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

    def validate_phone(self, field):
        from app.models.user import User
        if User.query.filter_by(phone=field.data.strip()).first():
            raise ValidationError('This phone number is already registered.')


class StaffForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])

    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Enter a valid email address.'),
        validate_real_email
    ])

    phone = StringField('Phone Number', validators=[
        DataRequired(),
        validate_nepal_phone,
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

    def validate_phone(self, field):
        from app.models.user import User
        if User.query.filter_by(phone=field.data.strip()).first():
            raise ValidationError('This phone number is already registered.')


class AdminStaffPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), validate_strong_password])
    confirm_password = PasswordField(
        'Confirm New Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match.')]
    )
    submit = SubmitField('Update Password')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Link')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), validate_strong_password])
    confirm_password = PasswordField(
        'Confirm New Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match.')]
    )
    submit = SubmitField('Reset Password')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), validate_strong_password])
    confirm_password = PasswordField(
        'Confirm New Password',
        validators=[DataRequired(), EqualTo('new_password', message='Passwords must match.')]
    )
    submit = SubmitField('Change Password')


class EditProfileForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Enter a valid email address.'),
        validate_real_email
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(),
        validate_nepal_phone,
    ])
    submit = SubmitField('Save Changes')

    def validate_phone(self, field):
        from flask_login import current_user
        from app.models.user import User
        phone = field.data.strip()
        existing = User.query.filter(User.phone == phone, User.id != current_user.id).first()
        if existing:
            raise ValidationError('This phone number is already registered.')