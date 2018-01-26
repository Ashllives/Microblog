import re
from app import db, app
from hashlib import md5

followers = db.Table('followers',
	db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
	db.Column('followed_id', db.Integer, db.ForeignKey('user.id')))

posthearts = db.Table('posthearts',
	db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
	db.Column('post_id', db.Integer, db.ForeignKey('post.id')),
	db.Column('timestamp', db.DateTime))

class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	nickname = db.Column(db.String(64), index=True, unique=True)
	email = db.Column(db.String(120), index=True, unique=True)
	posts = db.relationship('Post', backref='author', lazy='dynamic')
	about_me = db.Column(db.String(140))
	last_seen = db.Column(db.DateTime)
	followed = db.relationship('User',
								secondary=followers,
								primaryjoin=(followers.c.follower_id == id),
								secondaryjoin=(followers.c.followed_id == id),
								backref=db.backref('followers', lazy='dynamic'),
								lazy='dynamic')
	post_hearts = db.relationship('UserPostHearts', backref=db.backref('user_hearts', lazy='joined'),
								  lazy='dynamic', cascade='all, delete-orphan')

	@property
	def is_authenticated(self):
		return True

	@property
	def is_active(self):
		return True

	@property
	def is_anonymous(self):
		return False

	@staticmethod
	def make_unique_nickname(nickname):
		if User.query.filter_by(nickname=nickname).first() is None:
			return nickname
		version = 2
		while True:
			new_nickname = nickname + str(version)
			if User.query.filter_by(nickname=new_nickname).first() is None:
				break
			version += 1
		return new_nickname

	@staticmethod
	def make_valid_nickname(nickname):
		"""Function that takes a nickname and remove any characters that are not
		letters, numbers, the dot or the underscore."""
		return re.sub('[^a-zA-Z0-9_\.]', '', nickname)

	def get_id(self):
		try:
			return unicode(self.id) #python 2

		except NameError:
			return str(self.id) #python 3

	def avatar(self, size):
		return 'http://www.gravatar.com/avatar/%s?d=mm&s=%d' % (md5(self.email.encode('utf-8')).hexdigest(), size)

	def follow(self, user):
		if not self.is_following(user):
			self.followed.append(user)
			return self

	def unfollow(self, user):
		if self.is_following(user):
			self.followed.remove(user)
			return self

	def is_following(self, user):
		return self.followed.filter(followers.c.followed_id == user.id).count() > 0

	def did_heart(self, post):
		return self.post_hearts.filter(UserPostHearts.user_id == self.id).filter(UserPostHearts.post_id == post.id).count() > 0

	def followed_posts(self):
		return Post.query.join(followers, (followers.c.followed_id == Post.user_id)).filter(followers.c.follower_id == self.id).order_by(Post.timestamp.desc())

	def __repr__(self):
		return '<User %r>' %(self.nickname)

class Post(db.Model):
	__searchable__ = ['body']


	id = db.Column(db.Integer, primary_key=True)
	body = db.Column(db.String(140))
	timestamp = db.Column(db.DateTime)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	user_hearts = db.relationship('UserPostHearts', backref=db.backref('post_hearts', lazy='joined'),
								   lazy='dynamic', cascade='all, delete-orphan')

	def with_heart(self):
		return self.user_hearts.filter(UserPostHearts.post_id == self.id).count() > 0

	def __repr__(self):
		return '<Post %r>' %(self.body)

class UserPostHearts(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	timestamp = db.Column(db.DateTime)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	post_id = db.Column(db.Integer, db.ForeignKey('post.id'))

	def __repr__(self):
		return '<Timestamp %r>' %(self.timestamp)