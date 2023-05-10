import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

def lookup(symbol):
    url = "https://yfapi.net/v6/finance/quote"
    headers = {
        "accept": "application/json",
        "X-API-KEY": "MFjkkZtuB5JqYXgqkm8y8wmnF0quOQO41va0lCKg"
    }
    params = {
        "region": "US",
        "lang": "en",
        "symbols": symbol
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    stock_info = {}
    if response.status_code == 200:
        result = data["quoteResponse"]["result"][0]
        stock_info['symbol'] = result["symbol"]
        stock_info['price'] = result["regularMarketPrice"]
        stock_info['name'] = result["shortName"]

        return stock_info
    else:
        print("Failed to retrieve data from API.")

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print('helper.py - line 32')
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function




def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
