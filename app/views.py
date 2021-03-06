from flask import render_template, flash, redirect, session, url_for, request, g
from flask_login import login_user, logout_user, current_user, login_required
from flask_babel import gettext
from app import app, db, lm, oid, babel
from .forms import LoginForm, EditForm, PostForm, SearchForm
from datetime import datetime
from config import POSTS_PER_PAGE, MAX_SEARCH_RESULTS
from .models import User, Post, UserPostHearts
from .emails import follower_notification
from config import LANGUAGES

@lm.user_loader
def load_user(id):
	return User.query.get(int(id))

@babel.localeselector
def get_locale():
	return request.accept_languages.best_match(LANGUAGES.keys())

@app.before_request
def before_request():
	g.user = current_user
	if g.user.is_authenticated:
		g.user.last_seen = datetime.utcnow()
		db.session.add(g.user)
		db.session.commit()
		g.search_form = SearchForm()
	g.locale = get_locale()

@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
	if g.user is not None and g.user.is_authenticated:
		return redirect(url_for('index'))
	form=LoginForm()
	if form.validate_on_submit():
		session['remember me'] = form.remember_me.data
		return oid.try_login(form.openid.data, ask_for=['nickname', 'email'])

	return render_template('login.html',
							title="Sign In",
							form=form,
							providers=app.config['OPENID_PROVIDERS'])

@oid.after_login
def after_login(resp): # resp argument contains info returned by OpenID provider
	if resp.email is None or resp.email == "": 
		"""This is for validation. Valid email is required. If email was
		not provided, user cannot log in."""
		flash(gettext('Invalid login. Please try again.'))
		return redirect(url_for('login'))
	# search database for email provided. If email was not found,
	# user will be considered new user and added to the database
	user = User.query.filter_by(email=resp.email).first()
	if user is None: # in case of missing nickname, create one with split()
		nickname = resp.nickname
		if nickname is None or nickname == "":
			nickname = resp.email.split('@')[0]
		nickname = User.make_valid_nickname(nickname)
		nickname = User.make_unique_nickname(nickname)
		user = User(nickname=nickname, email=resp.email)
		db.session.add(user)
		db.session.commit()
		# make the user follow him/herself
		db.session.add(user.follow(user))
		db.session.commit()
	remember_me = False
	if 'remember_me' in session:
		remember_me = session['remember_me']
		session.pop('remember_me', None)
	login_user(user, remember=remember_me) # register as a valid login
	return redirect(request.args.get('next') or url_for('index'))

@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
	return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
	db.session.rollback()
	return render_template('500.html'), 500

# webpage controllers
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@app.route('/index/<int:page>', methods=['GET', 'POST'])
@login_required
def index(page=1):
	form = PostForm()

	if form.validate_on_submit():

		post = Post(body=form.post.data, 
					timestamp=datetime.utcnow(), 
					author=g.user)

		db.session.add(post)
		db.session.commit()

		flash(gettext('Your post is now live!'))

		return redirect(url_for('index'))
	posts = g.user.followed_posts().paginate(page, POSTS_PER_PAGE, False)
	
	return render_template("index.html",
							title='Home',
							form=form,
							posts=posts)

@app.route('/user/<nickname>')
@app.route('/user/<nickname>/<int:page>')
@login_required
def user(nickname, page=1):
	user = User.query.filter_by(nickname=nickname).first()

	if user == None:
		#flash(gettext('User %(nickname)s not found.', nickname=nickname))
		return redirect(url_for('index'))

	posts = user.posts.order_by(Post.timestamp.desc()).paginate(page, POSTS_PER_PAGE, False)

	return render_template('user.html',
							user=user,
							posts=posts)

@app.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
	form = EditForm(g.user.nickname)
	if form.validate_on_submit():
		g.user.nickname = form.nickname.data
		g.user.about_me = form.about_me.data
		db.session.add(g.user)
		db.session.commit()
		flash(gettext('Your changes have been saved.'))
		return redirect(url_for('edit'))
	elif request.method != "POST":
		form.nickname.data = g.user.nickname
		form.about_me.data = g.user.about_me
	return render_template('edit.html', form=form)

@app.route('/delete/<int:id>')
@login_required
def delete(id):
	post = Post.query.get(id)
	if post is None:
		flash(gettext('Post not found'))
		return redirect(url_for('index'))

	if post.author.id != g.user.id:
		flash(gettext('You cannot delete this post.'))
		return redirect(url_for('index'))
	db.session.delete(post)
	db.session.commit()
	flash(gettext('Your post has been deleted.'))
	return redirect(url_for('index'))

@app.route('/edit_post/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id, page=1):
	post = Post.query.get(id)
	form = PostForm(obj=post)
	
	if request.method == 'GET':
		form.post.data = post.body

		db.session.delete(post)
		db.session.commit()

	if request.method == 'POST' and form.validate_on_submit():
		new_post = request.form['post']

		to_post = Post(body=new_post, 
					timestamp=datetime.utcnow(), 
					author=g.user)

		db.session.add(to_post)
		db.session.commit()
		flash(gettext('Post updated.'))
		return redirect(url_for('index'))

	posts = g.user.followed_posts().paginate(page, POSTS_PER_PAGE, False)

	return render_template('index.html', 
							form=form,
							posts=posts)

@app.route('/heart_post/<int:id>', methods=['GET', 'POST'])
@login_required
def heart_post(id, page=1):
	post_to_heart = Post.query.filter_by(id=id).first()
	user_name = User.query.filter_by(nickname=g.user.nickname).first()
	
	if not g.user.did_heart(post_to_heart):
		heart = UserPostHearts(user_id=user_name.id, post_id=post_to_heart.id, timestamp=datetime.utcnow())
		db.session.add(heart)
		db.session.commit()
		return redirect(url_for('index'))


@app.route('/unheart_post/<int:id>', methods=['GET', 'POST'])
@login_required
def unheart_post(id, page=1):
	post = Post.query.filter_by(id=id).first()
	post_to_unheart = UserPostHearts.query.filter_by(post_id=post.id).first()
	user_name = User.query.filter_by(nickname=g.user.nickname).first()

	if g.user.did_heart(post):
		db.session.delete(post_to_unheart)
		db.session.commit()
		return redirect(url_for('index'))

@app.route('/follow/<nickname>')
@login_required
def follow(nickname):
	user  = User.query.filter_by(nickname=nickname).first()
	if user is None:
		flash(gettext('User ' + nickname + ' not found.'))
		return redirect(url_for('index'))

	if user == g.user:
		flash(gettext('You can\'t follow yourself!'))
		return redirect(url_for('user', nickname=nickname))

	u = g.user.follow(user)
	if u is None:
		flash(gettext('Cannot follow %(nickname)s.', nickname=nickname))
		return redirect(url_for('user', nickname=nickname))

	db.session.add(u)
	db.session.commit()

	flash(gettext('You are now following %(nickname)s!', nickname=nickname))
	follower_notification(user, g.user)
	return redirect(url_for('user', nickname=nickname))

@app.route('/unfollow/<nickname>')
@login_required
def unfollow(nickname):
	user = User.query.filter_by(nickname=nickname).first()
	if user is None:
		flash(gettext('User ' + nickname + ' not found.'))
		return redirect(url_for('index'))

	if user == g.user:
		flash(gettext('You can\'t unfollow yourself!'))
		return redirect(url_for('user', nickname=nickname))

	u = g.user.unfollow(user)
	if u is None:
		flash(gettext('Cannot unfollow %(nickname)s.', nickname=nickname))
		return redirect(url_for('user', nickname=nickname))

	db.session.add(u)
	db.session.commit()
	flash(gettext('You have stopped following %(nickname)s.', nickname=nickname))
	return redirect(url_for('user', nickname=nickname))

@app.route('/search', methods=['GET','POST'])
def search():
	if not g.search_form.validate_on_submit():
		flash(gettext('Invalid search.'))
		return redirect(url_for('index'))
	return redirect(url_for('search_results', query=g.search_form.search_user.data))

@app.route('/search_results/<query>')
@login_required
def search_results(query):
	results = User.query.filter_by(nickname=query).all()
	if results == []:
		flash(gettext("No results found for '%(query)s'.", query=query))

	return render_template('search_results.html',
							query=query,
							results=results)