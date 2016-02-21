from flask import Flask, redirect, url_for, render_template, request, json
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.login import LoginManager, UserMixin, login_user, logout_user,\
    current_user
from oauth import OAuthSignIn
import urllib2
import json
import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'top secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['OAUTH_CREDENTIALS'] = {
    'facebook': {
        'id': '154366911614208',
        'secret': '1b1566407beea556bc0dbd255a5c0b96'
    },
    'twitter': {
        'id': '3RzWQclolxWZIMq5LJqzRZPTl',
        'secret': 'm9TEd58DSEtRrZHpz2EjrV9AhsBRxKMo8m3kuIZj3zLwzwIimt'
    }
}

db = SQLAlchemy(app)
lm = LoginManager(app)
lm.login_view = 'index'


class User(UserMixin, db.Model):
  __tablename__ = 'users'
  id = db.Column(db.Integer, primary_key=True)
  social_id = db.Column(db.String(64), nullable=False, unique=True)
  nickname = db.Column(db.String(64), nullable=False)
  email = db.Column(db.String(64), nullable=True)

class Movie(db.Model):
  __tablename__ = 'movies'
  id = db.Column(db.Integer, primary_key = True)
  product = db.Column(db.PickleType)

# watched_films = db.Table('watched_films',
#   db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
#   db.Column('movie.id', db.Integer, db.ForeignKey('movie.id'))
# )

# watchlist = db.Table('watchlist',
#   db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
#   db.Column('movie.id', db.Integer, db.ForeignKey('movie.id'))
# )

@lm.user_loader
def load_user(id):
  return User.query.get(int(id))

watched_films = {}
watchlist = {}

def search_films():
  if request.form['action']:
    query = request.form["action"]

    results_URL = "http://metadata.sls1.cdops.net/SearchSuggestions/SystemId/e5ce3167-4e0b-4867-a8c3-c8f23aec5e71/DistributionChannel/20389393-b2e4-4f65-968e-75a5227e544c/SearchString/" + query + "/IncludeProducts/True"

    try:
      results = json.load(urllib2.urlopen(results_URL))["Products"]
    except: 
      results = ""

    return (results, query)

@app.route('/', methods=['GET', 'POST'])
def index():
  if request.method == "POST":
    ret = search_films()
    return render_template('results.html', results = ret[0], query = ret[1])

  # carousel of most popular or recommended films, then browse per genre below? 

  # For retrieving films per genre 

  # films_URL = "http://metadata.sls1.cdops.net/Categories/SystemId/e5ce3167-4e0b-4867-a8c3-c8f23aec5e71/DistributionChannel/20389393-b2e4-4f65-968e-75a5227e544c/Id/3338/IncludeChildren/True"
  # film_cats = json.load(urllib2.urlopen(films_URL))
  # genres = film_cats["Categories"][0]["Children"]

  # products_URL = "https://services.sls1.cdops.net/Subscriber/SearchProducts/SystemID/e5ce3167-4e0b-4867-a8c3-c8f23aec5e71/DistributionChannel/20389393-b2e4-4f65-968e-75a5227e544c/Categories/"
  # products = {}

  # for genre in genres:
  #   genre_id = genre["Id"]
  #   URL = products_URL + str(genre_id)
  #   products[genre_id] = json.load(urllib2.urlopen(URL))["Products"]

  return render_template('index.html') #, genres = genres, products = products

@app.route('/logout')
def logout():
  logout_user()
  return redirect(url_for('index'))


@app.route('/authorize/<provider>')
def oauth_authorize(provider):
  if not current_user.is_anonymous:
    return redirect(url_for('signin'))
  oauth = OAuthSignIn.get_provider(provider)
  return oauth.authorize()


@app.route('/callback/<provider>')
def oauth_callback(provider):
  if not current_user.is_anonymous:
    return redirect(url_for('signin'))
  oauth = OAuthSignIn.get_provider(provider)
  social_id, username, email = oauth.callback()
  if social_id is None:
    flash('Authentication failed.')
    return redirect(url_for('signin'))
  user = User.query.filter_by(social_id=social_id).first()
  if not user:
    user = User(social_id=social_id, nickname=username, email=email)
    db.session.add(user)
    db.session.commit()
  login_user(user, True)
  return redirect(url_for('signin'))

@app.route('/product.html', methods=['GET', 'POST'])
def show_product():
  product_id = request.args.get('productID')

  product = Movie.query.filter_by(id=product_id).first()
  if not product:
    product_URL = "http://metadata.sls1.cdops.net/Product/SystemId/e5ce3167-4e0b-4867-a8c3-c8f23aec5e71/DistributionChannel/20389393-b2e4-4f65-968e-75a5227e544c/Id/" + str(product_id)
    product = json.load(urllib2.urlopen(product_URL))["Product"]
    prod = Movie(id=product_id, product=product)
    db.session.add(prod)
    db.session.commit()
  else:
    product = product.product

  watched = ""
  listed = ""

  if request.method == "POST":
    print request.form["action"]
    if request.form["action"] == "Mark as Watched": # mark film as watched 
      watched_films[product_id] = (product, datetime.datetime.now())
      if product_id in watchlist: # remove film from watchlist if necessary
        del watchlist[product_id] 
      watched = "true"
    elif request.form["action"] == "Add to Watchlist": # add film to watch list
      watchlist[product_id] = (product, datetime.datetime.now())
      listed = "true"
    else:
      ret = search_films()
      return render_template('results.html', results = ret[0], query = ret[1])
  else:
    if product_id in watchlist:
      listed = "true"
    elif product_id in watched:
      watched = "true"

  return render_template('product.html', product = product, watched = watched, listed = listed)

@app.route('/lists.html', methods=['GET', 'POST'])
def show_lists():
  if request.method == "POST":
    ret = search_films()
    return render_template('results.html', results = ret[0], query = ret[1])

  films = []

  for k in watchlist:
    films.append(watchlist[k])

  sorted_list = sorted(films, key=lambda x: x[1], reverse=False) 

  watched = []
  for k in watched_films:
    watched.append(watched_films[k])

  rec_watched = sorted(watched, key=lambda x: x[1], reverse=True) 

  return render_template('lists.html', list = sorted_list, rec_watched = rec_watched)

@app.route('/signin.html', methods=['GET', 'POST'])
def signin():
  return render_template('signin.html')

if __name__ == '__main__':
    db.create_all()
    port = int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0', port=port)