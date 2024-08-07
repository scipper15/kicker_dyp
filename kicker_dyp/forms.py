from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import (PasswordField, StringField, validators, SubmitField,
                     FileField, IntegerField, DateField, SelectField)


class RegistrationForm(FlaskForm):
    username = StringField('Username', [
        validators.DataRequired(),
        validators.Length(min=4, max=25),
    ])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm_password',
                           message='Passwords must match.'),
        validators.Length(min=4, max=25),
    ])
    confirm_password = PasswordField('Confirm Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm_password',
                           message='Passwords must match.'),
    ])
    submit = SubmitField(description='Submit')


class LoginForm(FlaskForm):
    username = StringField('Username', [
        validators.DataRequired(),
    ])
    password = PasswordField('Password', [
        validators.DataRequired(),
    ])
    submit = SubmitField(description='Login')


class UploadForm(FlaskForm):
    zip_file = FileField('Upload ZIP File', validators=[
                         FileRequired(), FileAllowed(['zip'], 'Only ZIP files, please.')])
    submit = SubmitField('Upload')


class SettingsForm(FlaskForm):
    dyp_year = IntegerField('DYP Series Year', [
        validators.InputRequired(),
    ])
    dyp_season = IntegerField('DYP Series Season', [
        validators.InputRequired(),
    ])
    dyp_start = DateField('Startdatum DYP', [
        validators.InputRequired(),
    ])
    dyp_end = DateField('Enddatum DYP', [
        validators.InputRequired(),
    ])
    submit = SubmitField('Save')


class RevertForm(FlaskForm):
    match_day = SelectField(
        'Everything until including DYP Match Day will be purged from database',
        [validators.InputRequired()],
        coerce=int
    )
    submit = SubmitField(
        'Click to revert database now! This is NOT reversible!')
