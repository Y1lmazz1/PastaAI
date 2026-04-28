from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from models import User


class RegisterForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[
        DataRequired(message='Bu alan zorunludur.'),
        Length(min=3, max=30, message='Kullanıcı adı 3-30 karakter olmalıdır.')
    ])
    password = PasswordField('Şifre', validators=[
        DataRequired(message='Bu alan zorunludur.'),
        Length(min=6, message='Şifre en az 6 karakter olmalıdır.')
    ])
    confirm_password = PasswordField('Şifre Tekrar', validators=[
        DataRequired(message='Bu alan zorunludur.'),
        EqualTo('password', message='Şifreler eşleşmiyor.')
    ])
    role = SelectField('Hesap Türü', choices=[
        ('customer', 'Müşteriyim'),
        ('admin', 'Pastane Sahibiyim')
    ])
    submit = SubmitField('Kayıt Ol')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Bu kullanıcı adı zaten alınmış.')


class LoginForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[
        DataRequired(message='Bu alan zorunludur.')
    ])
    password = PasswordField('Şifre', validators=[
        DataRequired(message='Bu alan zorunludur.')
    ])
    submit = SubmitField('Giriş Yap')