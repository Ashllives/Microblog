import os
from flask import Flask
from flask.json import JSONEncoder
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_openid import OpenID
from flask_mail import Mail
from flask_babel import Babel, lazy_gettext
from config import basedir, ADMINS, MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD
from .momentjs import momentjs

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)

lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'

# def _gettext(msg):
# 	return gettext(msg)
# lm.localize_callback = gettext

lm.login_message = lazy_gettext('Please log in to access this page.')
oid = OpenID(app, os.path.join(basedir, 'tmp'))
mail = Mail(app)
babel = Babel(app)

class CustomJSONEncoder(JSONEncoder):
	"""This class adds support for lazy translation texts to Flask's
	JSON Encoder. This is necessary when flashing translated texts.
	This installs a custom JSON encoder that forces the lazy texts to
	be evaluated into strings prior to being converted to JSON."""
	def default(self, obj):
		from speaklater import is_lazy_string
		if is_lazy_string(obj):
			try:
				return unicode(obj) # python 2
			except NameError:
				return str(obj) # python 3

		return super(CustomJSONEncoder, self).default(obj)

app.json_encoder = CustomJSONEncoder

if not app.debug:
	import logging
	from logging.handlers import SMTPHandler
	credentials = None
	if MAIL_USERNAME or MAIL_PASSWORD:
		credentials = (MAIL_USERNAME, MAIL_PASSWORD)
	mail_handler = SMTPHandler((MAIL_SERVER, MAIL_PORT), 'no-reply@' + MAIL_SERVER, ADMINS, 'microblog failure', credentials)
	mail_handler.setLevel(logging.ERROR)
	app.logger.addHandler(mail_handler)

if not app.debug:
	import logging
	from logging.handlers import RotatingFileHandler
	file_handler = RotatingFileHandler('microblog/tmp/microblog.log', 'a', 1 * 1024 * 1024, 10)
	file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
	app.logger.setLevel(logging.INFO)
	file_handler.setLevel(logging.INFO)
	app.logger.addHandler(file_handler)
	app.logger.info('microblog startup')

app.jinja_env.globals['momentjs'] = momentjs

from app import views, models

