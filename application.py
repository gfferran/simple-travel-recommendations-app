import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import error, success, login_required, get_coordinates, get_country, distance_between
import json
from operator import itemgetter




# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///theocean.db")

## Index
@app.route("/", methods=["GET"])
@login_required
def index():
    return render_template("index.html")

## ADD A PLACE
@app.route("/add", methods=["GET", "POST"])
@login_required
def add():

    if request.method == "POST":
        # Check all fields are filled
        if not request.form.get("placename"):
            return error("Please add name of the place.")
        elif not request.form.get("latitude"):
            return error("Please add latitude of the place.")
        elif not request.form.get("longitude"):
            return error("Please add longitude of the place.")
        elif not request.form.get("country"):
            return error("Please add country of the place.")

        # Store new place into users database
        placeKeyId = db.execute("INSERT INTO places (placename, latitude, longitude, register_user_id, country, ratings_avg, ratings_num) VALUES (:placename, :latitude, :longitude, :user_id, :country, :ratings_avg, :ratings_num)",
                                placename=request.form.get("placename"),
                                latitude=request.form.get("latitude"),
                                longitude=request.form.get("longitude"),
                                user_id=session["user_id"],
                                country=request.form.get("country"),
                                ratings_avg=0,
                                ratings_num=0)

        if request.form.get("description"):
            db.execute("UPDATE places SET description = :description WHERE placename = :placename",
                        description=request.form.get("description"),
                        placename=request.form.get("placename"))

        return success("Place added successfully.")

    else:
        return render_template("add.html")

## CHANGE PASSWORD
@app.route("/changeusername", methods=["GET", "POST"])
@login_required
def changeusername():

    if request.method == "POST":
        # Check all fields are filled
        if not request.form.get("newusername"):
            return error("Please introduce your new username.")
        elif not request.form.get("currentpassword"):
            return error("Please introduce your password.")

        # Check old password is correct
        rows = db.execute("SELECT * FROM users WHERE user_id = :user_id", user_id=session["user_id"])

        if check_password_hash(rows[0]["hash"], request.form.get("currentpassword")):
            username = request.form.get("newusername")
            db.execute("UPDATE users SET username = :username WHERE user_id = :user_id", username=username, user_id=session["user_id"])
        else:
            return error("Password is not correct.")

        # Redirect to homepage after changing password
        success_msg = "Username changed. You shall be " + username + " from now on."
        return success(success_msg)

    else:
        return render_template("editaccount.html")

## CHANGE PASSWORD
@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changepassword():

    if request.method == "POST":
        # Check all fields are filled
        if not request.form.get("currentpassword"):
            return error("Please introduce your current password.")
        elif not request.form.get("newpassword"):
            return error("Please introduce your new password.")
        elif not request.form.get("confirmation"):
            return error("Please introduce the confirmation of your new password.")
        elif request.form.get("newpassword") != request.form.get("confirmation"):
            return error("New passwords don't match. Try again.")

        # Check old password is correct
        rows = db.execute("SELECT * FROM users WHERE user_id = :user_id", user_id=session["user_id"])

        if check_password_hash(rows[0]["hash"], request.form.get("currentpassword")):
            hash = generate_password_hash(request.form.get("newpassword"))
            db.execute("UPDATE users SET hash = :hash WHERE user_id = :user_id", hash=hash, user_id=session["user_id"])
        else:
            return error("Current password is not correct.")

        # Redirect to homepage after changing password
        return success("Password changed successfully.")

    else:
        return render_template("editaccount.html")

## EDIT ACCOUNT
@app.route("/editaccount", methods=["GET"])
@login_required
def editaccount():

    return render_template("editaccount.html")

## DELETE RATING
@app.route("/delete_rating", methods=["GET","POST"])
@login_required
def delete_rating():

    # POST
    if request.method == "POST":

        # Get place_id
        place_id = request.form.get("place_id")

        # Get ratings of place
        rows_place= db.execute("SELECT * FROM places WHERE place_id = :place_id",place_id=place_id)

        # Get ratings of user
        rows_user = db.execute("SELECT * FROM users WHERE user_id = :user_id",user_id=session["user_id"])
        ratings_json = rows_user[0]["ratings"]
        ratings = json.loads(ratings_json)
        old_rating = float(ratings[place_id])

        # Get rating from the place
        old_ratings_avg = float(rows_place[0]["ratings_avg"])
        old_ratings_num = float(rows_place[0]["ratings_num"])

        if old_ratings_num > 1:
            new_ratings_avg = (old_ratings_avg * old_ratings_num - old_rating)/(old_ratings_num - 1)
        else:
            new_ratings_avg = 0

        new_ratings_num = old_ratings_num - 1

        # Update place in database
        db.execute("UPDATE places SET ratings_avg = :ratings_avg, ratings_num = :ratings_num WHERE place_id = :place_id",
            place_id=place_id,
            ratings_avg = new_ratings_avg,
            ratings_num = int(new_ratings_num))

        # Update ratings of user_id
        ratings.pop(str(place_id))
        ratings_json = json.dumps(ratings)
        db.execute("UPDATE users SET ratings = :ratings WHERE user_id = :user_id", ratings=ratings_json, user_id=session["user_id"])

        return redirect(request.referrer)

    # GET
    else:
        return redirect(request.referrer)

## LOGIN
@app.route("/login", methods=["GET","POST"])
def login():

    # Forget any user_id
    session.clear()

    if request.method == "POST":

        # Check all fields are filled
        if not request.form.get("username"):
            return error("Please insert a username.")
        elif not request.form.get("password"):
            return error("Please insert a password.")

        # Query users database for user_id info
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Check password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return error("Invalid username and/or password.")

        # Remember which user has logged in
        session["user_id"] = rows[0]["user_id"]

        # Redirect user to homepage
        return redirect("/")

    else:
        # Return to login page
        return render_template("login.html")

## LOGOUT
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


## NEARBY PLACES
@app.route("/nearby", methods=["GET"])
@login_required
def nearby():

    # Get current location
    geo_data = get_coordinates()
    geo_lat = float(geo_data["latitude"])
    geo_lon = float(geo_data["longitude"])

    # Get current country
    country_data = get_country()
    country_name = country_data["name"]

    # Get all places
    places = db.execute("SELECT * FROM places WHERE country =:country", country=country_name)

    # Get user to check for previous ratings
    rows_user = db.execute("SELECT * FROM users WHERE user_id = :user_id",user_id=session["user_id"])
    if rows_user[0]["ratings"]:
        ratings_json = rows_user[0]["ratings"]
        ratings = json.loads(ratings_json)

    # Add distance to places
    for place in places:
        distance = distance_between(geo_lat,geo_lon,place["latitude"],place["longitude"])
        place["distance"] = format(distance, '.2f')

        # Add my_rating
        place_id = place["place_id"]
        if ratings:
            if str(place_id) in ratings:
                place["my_rating"] =  float(ratings[str(place_id)])


    # Sort places by distance
    places_bydistance = sorted(places, key=lambda distance: float(distance["distance"]), reverse=False)
    places_bydistance = places_bydistance[:30]

    # Additional text: coordinates of user
    current_location = [geo_lat, geo_lon]
    additional_text = "Your location is: " + str(current_location[0]) + ", " + str(current_location[1]) + "."

    return render_template("places.html",
        title="Nearby places",
        subtitle="Cool places nearby",
        places=places_bydistance,
        additional_text=additional_text,
        list_type="nearby")

## POPULAR
@app.route("/popular", methods=["GET", "POST"])
@login_required
def popular():

    # Get country info
    country_data = get_country()
    country_name = country_data["name"]

    # Select 10 elements in database with country=country OR country=country3 sorted by rating
    places_byrating = db.execute("SELECT * FROM places WHERE country =:country ORDER BY ratings_avg DESC LIMIT 10",country=country_name)

    # Get location info
    geo_data = get_coordinates()
    geo_lat = float(geo_data["latitude"])
    geo_lon = float(geo_data["longitude"])

    # Text atop the list
    additional_text = "Highest-rated places in " + country_name + "."

    # Get user to check for previous ratings
    rows_user = db.execute("SELECT * FROM users WHERE user_id = :user_id",user_id=session["user_id"])
    if rows_user[0]["ratings"]:
        ratings_json = rows_user[0]["ratings"]
        ratings = json.loads(ratings_json)

    # Add elements to the info to print
    for place in places_byrating:

        # Calculate distance
        distance = distance_between(geo_lat,geo_lon,place["latitude"],place["longitude"])
        place["distance"] = format(distance, '.2f')

        # Add my_rating
        place_id = place["place_id"]
        if ratings:
            if str(place_id) in ratings:
                place["my_rating"] =  float(ratings[str(place_id)])

    return render_template("places.html",
        title="Popular places",
        subtitle="Popular places",
        places=places_byrating,
        additional_text=additional_text,
        list_type="popular")

## RATE
@app.route("/rate", methods=["GET", "POST"])
@login_required
def rate():

    if request.method == "POST":

        # Get rating and place_id values

        place_id = request.form.get("place_id")

        # Get user_id and place_id
        rows_user = db.execute("SELECT * FROM users WHERE user_id = :user_id",user_id=session["user_id"])
        rows_place= db.execute("SELECT * FROM places WHERE place_id = :place_id",place_id=place_id)

        # Make sure SELECT commands worked
        if not rows_user:
            return error("Database error (Users). Command not executed.")
        elif not rows_place:
            return error("Database error (Places). Command not executed.")

        # Ratings of user
        ratings_json = rows_user[0]["ratings"]

        # If user has no ratings, create new dict with ratings
        if not ratings_json:
            ratings = dict()
        # Else, convert JSON to Python dict
        else:
            ratings = json.loads(ratings_json)

        # Get rating from the place
        new_rating = float(request.form.get("rating"))
        old_ratings_avg = float(rows_place[0]["ratings_avg"])
        old_ratings_num = float(rows_place[0]["ratings_num"])

        # Update rating if place_id already in ratings
        if str(place_id) in ratings:
            old_rating = float(ratings[place_id])
            new_ratings_avg = (old_ratings_avg * old_ratings_num - old_rating + new_rating)/(old_ratings_num)
            new_ratings_num = old_ratings_num
            ratings[place_id] = new_rating
        # Otherwise, add new rating to the avg and num
        else:
            new_ratings_avg = (old_ratings_avg * old_ratings_num + new_rating)/(old_ratings_num + 1)
            new_ratings_num = old_ratings_num + 1

        db.execute("UPDATE places SET ratings_avg = :ratings_avg, ratings_num = :ratings_num WHERE place_id = :place_id",
            place_id=place_id,
            ratings_avg = new_ratings_avg,
            ratings_num = int(new_ratings_num))

        # Update ratings of user_id
        ratings[str(place_id)] = new_rating
        ratings_json = json.dumps(ratings)
        db.execute("UPDATE users SET ratings = :ratings WHERE user_id = :user_id", ratings=ratings_json, user_id=session["user_id"])

        return redirect(request.referrer)

    else:
        return redirect(request.referrer)

## RATINGS
@app.route("/ratings", methods=["GET", "POST"])
@login_required
def ratings():

    # Get user_id and place_id
    rows_user = db.execute("SELECT * FROM users WHERE user_id = :user_id", user_id=session["user_id"])
    print(rows_user)
    if not rows_user:
        return error("Username doesn't exist.")


    # Get user ratings
    ratings_json = rows_user[0]["ratings"]

    # If user has no ratings, create new dict with ratings
    if not ratings_json:
        return error("You have not rated any places yet!")
    # Else, convert JSON to Python dict
    else:
        ratings = json.loads(ratings_json)
        additional_text = rows_user[0]["username"] + "'s rated places, sorted by rating."

        # Create empty list
        rated_places = list()

        # Go through users' ratings
        for place_id, my_rating in ratings.items():
            # Get the rated place
            row_place = db.execute("SELECT * FROM places WHERE place_id = :place_id",place_id=place_id)
            # add rating
            row_place[0]["my_rating"] = int(my_rating)
            # add place_id to places
            rated_places.append(row_place[0])

        # Sort by rating
        rated_places = sorted(rated_places, key=lambda my_rating: int(my_rating["my_rating"]), reverse=True)

        return render_template("places.html",
            title="My ratings",
            subtitle="My ratings",
            additional_text=additional_text,
            places=rated_places,
            list_type="ratings")

## REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # Check all fields are filled
        if not request.form.get("username"):
            return error("Please provide a username.")
        elif not request.form.get("password"):
            return error("Please provide a password.")
        elif request.form.get("password") != request.form.get("confirmation"):
            return error("Passwords don't match.")

        # Hash password
        hash = generate_password_hash(request.form.get("password"))

        # JSON of ratings
        ratings = dict()
        ratings = json.dumps(ratings)

        # Store new user into users database
        keyId = db.execute("INSERT INTO users (username, hash, ratings) VALUES (:username, :hash, :ratings)", username=request.form.get("username"), hash=hash, ratings=ratings)

        # Check if username already exists
        if not keyId:
            return error("Could not create user. (Database error)")

        # Log in the user
        session["user_id"] = keyId

        # Go back to homepage
        return redirect("/")

    else:
        # Redirect to register
        return render_template("register.html")
