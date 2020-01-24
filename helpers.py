import os
import requests
from math import sin, cos, sqrt, atan2, radians
from flask import redirect, render_template, request, session
from functools import wraps

# Added by me
def error(message):
    return render_template("error.html", message=message)

def success(message):
    return render_template("success.html", message=message)


# Re-used from CS50 Finance
def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def get_coordinates():
    # Info: https://www.geojs.io/docs/v1/endpoints/
    ip_request = requests.get('https://get.geojs.io/v1/ip.json')
    my_ip = ip_request.json()['ip']

    geo_request = requests.get('https://get.geojs.io/v1/ip/geo/' + my_ip + '.json')
    geo_data = geo_request.json()

    return geo_data

def get_country():
    ip_request = requests.get('https://get.geojs.io/v1/ip.json')
    my_ip = ip_request.json()['ip']

    country_requests = requests.get('https://get.geojs.io/v1/ip/country/' + my_ip + '.json')
    country_data = country_requests.json()

    return country_data

def distance_between(lat1,lon1,lat2,lon2):

    # Earth's radius
    R = 6373.0

    # Convert DEG to RAD
    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return distance