#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
import sys
import psycopg2
import csv
from datetime import date, datetime

#----------------------------------------------------------------------------#
#   connection to local host postgreSQL database and App Config
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app,db)

# An Association Model was created opposed to a Table to ensure that the "start_time" attribute can also be created
# This table enables many-to-many relationships between VENUE and ARTIST classes
class Shows(db.Model):
    __tablename__='shows'

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'))
    artist_id = db.Column(db.Integer,db.ForeignKey('artist.id'))
    artist = db.relationship("Artist", backref=db.backref('venue'))
    venue = db.relationship("Venue", backref=db.backref('artist'))

#Respective data model structure for a Venue
class Venue(db.Model):
    __tablename__ = 'venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    genres = db.Column(db.String(200))
    image_link = db.Column(db.String(500))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(200),default="Not looking for talent")
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))

    def __repr__(self):
      return f'<Venue ID: {self.id}, name: {self.name}>'

#Respective data model structure for an Artist
class Artist(db.Model):
    __tablename__ = 'artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120), nullable = False)
    genres = db.Column(db.String(120))
    seeking_venue= db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(200),default="Not looking for a new venue")
    image_link = db.Column(db.String(500))
    website = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))

    def __repr__(self):
      return f'<Artist ID: {self.id}, name: {self.name}>'


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format = "EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # View the available venues according to city and state
  
  venue_data = Venue.query.order_by(Venue.city).order_by(Venue.state).all()
  current_time = datetime.now().strftime('%Y-%m-%d %H:%S:%M')
  new_data = []
  #the "new+city_state" variable seeks to identify new patterns between CITY and STATE attributes so that the corresponding structure required by the HTML form can be maintained.
  #If a pattern exists, new venue information is appended, otherwise a new relationship pattern is created to which new venue information is appended
  new_city_state = ''

  for venue in venue_data:
    if new_city_state == venue.city + venue.state:
      new_data[len(new_data)-1]["venues"].append({
        "id": venue.id,
        "name":venue.name,
        #The variable below serves no purpose as it cannot be displayed on the form. Note the number of upcoing shows has been calculated and is included for each of the venue views
        "num_upcoming_shows": 0
      })
    else:
      new_city_state = venue.city + venue.state
      new_data.append({
        "city":venue.city,
        "state":venue.state,
        "venues": [{
          "id": venue.id,
          "name":venue.name,
          #The variable below serves no purpose as it cannot be displayed on the form. Note the number of upcoing shows has been calculated and is included for each of the venue views
          "num_upcoming_shows": 0
        }]
      })
  return render_template('pages/venues.html', areas=new_data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # Provide a search functionality on venues
  search_term=request.form.get('search_term', '')
  new_term=str('%'+search_term+'%')
  try:
    response=db.session.query(Venue).filter(Venue.name.ilike(new_term)).order_by('name').all()
  except: 
    response=str(search_term)+" not registered on the platoform"
  finally:
    return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue information for a given venue_id as well as the number and respective shows that will or has happened at this venue
  venue=Venue.query.get(venue_id)
  s = db.session.query(Artist.id,Artist.name,Artist.image_link,Shows.start_time,Shows.venue_id).join(Shows, Shows.artist_id==Artist.id).filter(Shows.venue_id==venue_id)
  upcoming_shows =  s.filter(Shows.start_time >= datetime.now())
  completed_artists = s.filter(Shows.start_time < datetime.now())
  nr_upcoming_shows = upcoming_shows.count()
  nr_completed_shows = completed_artists.count()
  upcoming_artists = upcoming_shows.all()
  completed_artists = completed_artists.all()
  
  venue.upcoming_shows = []
  for u in upcoming_artists:
    artist_id=u[0]
    artist_name =u[1]
    artist_image_link=u[2]
    start_time = u[3].strftime("%Y%m%d %H:%M:%S")
    venue.upcoming_shows.append({'artist_id': artist_id, "artist_name": artist_name, "artist_image_link": artist_image_link, "start_time": start_time})
  
  venue.comp_art = []
  for c in completed_artists:
    artist_id=c[0]
    artist_name =c[1]
    artist_image_link=c[2]
    start_time = c[3].strftime("%Y%m%d %H:%M:%S")
    venue.comp_art.append({'artist_id': artist_id, "artist_name": artist_name, "artist_image_link": artist_image_link, "start_time": start_time})

  data={
    "id": venue.id,
    "name": venue.name,
    "genres": [venue.genres],
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": venue.comp_art,
    "upcoming_shows": venue.upcoming_shows,
    "past_shows_count": nr_completed_shows,
    "upcoming_shows_count": nr_upcoming_shows,
  }
  return render_template('pages/show_venue.html', venue=data)


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
#Gets a respective Venues information from a form and writes it to a database
def create_venue_submission():
  error = False
  body = {}
  try:
    name = request.form.get('name', '')
    city = request.form.get('city', '')
    state = request.form.get('state', '')
    address = request.form.get('address', '')
    phone = request.form.get('phone', '')
    genres = request.form.get('genres', '')
    facebook_link = request.form.get('facebook_link', '')
    seeking_description = str("Not looking for talent")
    venue = Venue(
      name=name, 
      city=city, 
      state=state, 
      address=address,
      phone=phone,
      genres=genres,
      facebook_link=facebook_link, 
      seeking_talent=False, 
      seeking_description = seeking_description, 
      website = facebook_link)
    db.session.add(venue)
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
    flash('Venue ' + request.form['name'] + ' experienced problems')
  finally:
    db.session.close()

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # omplete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  return None

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # replace with real data returned from querying the database
  data=Artist.query.all()
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  search_term=request.form.get('search_term', '')
  print("The search term is"+search_term)
  new_term=str('%'+search_term+'%')
  print("The new term is "+new_term)
  response=db.session.query(Artist).filter(Artist.name.ilike(new_term)).order_by('name').all()
  print("The response is....."+str(response))
  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id
  artist = Artist.query.get(artist_id)
  nr_upcoming_shows = db.session.query(Venue,Shows).join(Shows, Shows.venue_id==Venue.id).filter(Shows.artist_id==artist_id,Shows.start_time >= datetime.now()).count()
  nr_completed_shows = db.session.query(Venue,Shows).join(Shows, Shows.venue_id==Venue.id).filter(Shows.artist_id==artist_id,Shows.start_time < datetime.now()).count()
  upcoming_shows = db.session.query(Venue.id, Venue.name, Venue.image_link, Shows.start_time, Shows.artist_id).join(Shows, Shows.venue_id==Venue.id).filter(Shows.artist_id==artist_id,Shows.start_time >= datetime.now()).all()
  completed_shows = db.session.query(Venue.id, Venue.name, Venue.image_link, Shows.start_time, Shows.artist_id).join(Shows, Shows.venue_id==Venue.id).filter(Shows.artist_id==artist_id,Shows.start_time < datetime.now()).all()
  
  artist.up_shows = []
  for u in upcoming_shows:
    u_venue_id=u[0]
    u_venue_name =u[1]
    u_venue_image_link=u[2]
    u_start_time = u[3].strftime("%Y%m%d %H:%M:%S")
    artist.up_shows.append({'venue_id': u_venue_id, "venue_name": u_venue_name, "venue_image_link": u_venue_image_link, "start_time": u_start_time})
  
  print("Upcoming shows")
  print(artist.up_shows)

  artist.comp_shows = []
  for c in completed_shows:
    c_venue_id=c[0]
    c_venue_name =c[1]
    c_venue_image_link=c[2]
    c_start_time = c[3].strftime("%Y%m%d %H:%M:%S")
    artist.comp_shows.append({'venue_id': c_venue_id, "venue_name": c_venue_name, "venue_image_link": c_venue_image_link, "start_time": c_start_time})
  print("completed shows")
  print(artist.comp_shows)

  data1={
    "id": artist.id,
    "name": artist.name,
    "genres": [artist.genres],
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": artist.comp_shows,
    "upcoming_shows": artist.up_shows,
    "past_shows_count": nr_completed_shows,
    "upcoming_shows_count": nr_upcoming_shows
  }
  return render_template('pages/show_artist.html', artist=data1)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = Artist.query.get(artist_id)
  artist={
   "id": artist.id,
    "name": artist.name,
    "genres": [artist.genres],
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link
  }
  # TODO: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
   # populate form with values from venue with ID <venue_id>
  form = VenueForm()
  venue=Venue.query.get(venue_id)
  venue={
     "id": venue.id,
    "name": venue.name,
    "genres": [venue.genres],
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
  }
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  # insert form data as a new Venue record in the db, instead
  # modify data to be the data object returned from db insertion
  error = False
  body = {}
  try:
    name = request.form.get('name', '')
    city = request.form.get('city', '')
    state = request.form.get('state', '')
    phone = request.form.get('phone', '')
    genres = request.form.get('genres', '')
    facebook_link = request.form.get('facebook_link', '')
    artist = Artist(name=name, city=city, state=state, phone=phone,genres=genres,facebook_link=facebook_link)
    db.session.add(artist)
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
    flash('ERROR: Artist ' + request.form['name'] + ' not listed')
  finally:
    db.session.close()
  # on successful db insert, flash success 
  # on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  # replace with real venues data.
  query_data=Shows.query.all()
  new_data = []
  for d in  query_data:
    venue_name = str(db.session.query(Venue.name).filter(Venue.id==d.venue_id).all()[0][0])
    artist_name = str(db.session.query(Artist.name).filter(Artist.id==d.artist_id).all()[0][0])
    new_data.append({"start_time": str(d.start_time), "artist_image_link": "Empty", "venue_id":d.venue_id, "venue_name":venue_name, "artist_id": d.artist_id, "artist_name":artist_name}) 
  
  return render_template('pages/shows.html', shows=new_data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead
  error = False
  body = {}
  try:
    artist_id = int(request.form.get('artist_id', ''))
    venue_id = int(request.form.get('venue_id', ''))
    time = request.form.get('start_time', '')
    start_time = format_datetime(time)
    show = Shows(start_time=start_time, venue_id = venue_id, artist_id = artist_id)
    db.session.add(show)
    db.session.commit()
    flash('Show was successfully listed!')
  except:
    error = True
    db.session.rollback()
    print(sys.exc_info())
    flash('ERROR - Show was not listed!')
  finally:
    db.session.close()

  # on successful db insert, flash success
  # on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Show could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
