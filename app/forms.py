from flask_wtf import Form
from wtforms import StringField, BooleanField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_babel import gettext
from app.models import User

class LoginForm(Form):
	"""creates a login form"""
	openid=StringField('openid', validators=[DataRequired()])
	remember_me=BooleanField('remember_me', default=False)

class EditForm(Form):
	"""Allows users to edit their profile"""
	nickname = StringField('nickname', validators=[DataRequired()])
	about_me = TextAreaField('about_me', validators=[Length(min=0, max=140)])

	def __init__(self, original_nickname, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)
		self.original_nickname = original_nickname

	def validate(self):
		if not Form.validate(self):
			return False
		if self.nickname.data == self.original_nickname:
			return True
		if self.nickname.data != User.make_valid_nickname(self.nickname.data):
			self.nickname.errors.append(gettext('This nickname has invalid characters. Please use letters, numbers, dots and underscores only.'))
			return False
		user = User.query.filter_by(nickname=self.nickname.data).first()
		if user != None:
			self.nickname.errors.append(gettext('This nickname is already in use. Please choose another one.'))
			return False
		return True

class PostForm(Form):
	post = StringField('post', validators=[DataRequired()])

class SearchForm(Form):
	"""Search users from database"""
	search_user = StringField('Search', validators=[DataRequired('Search user.')])