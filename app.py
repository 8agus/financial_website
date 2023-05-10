import datetime

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from flask_session import Session
from helpers import apology, login_required, usd, lookup
# from test import lookup

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    if request.method == "GET":

        # Get information of share holding  and balances from database
        shares = db.execute("SELECT * FROM share_register WHERE user_id = ?", session["user_id"])
        cash_balance = db.execute("SELECT cash, username FROM users WHERE id = ?", session["user_id"])

        total_all_shares = 0
        for share in shares:
            # Get live price of share and add to shares
            live_price = lookup(share["symbol"])
            share["live_price"] = int(live_price['price'])

            # Get total value live price value per transaction and add to shares
            total_per_share = int(live_price['price']) * int(share["number"])
            share["total_per_share"] = total_per_share

            # Get total value of all share transactions on share register
            total_all_shares += share["total_per_share"]

        # Get value of cash and stock
        cash_plus_shares = int(cash_balance[0]["cash"]) + total_all_shares

        return render_template("index.html", shares=shares, balance=usd(cash_balance[0]["cash"]), cash_plus_shares=usd(cash_plus_shares), user_id=cash_balance[0]["username"])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # Call buy HTML template
    if request.method == "GET":
        return render_template("buy.html")

    # Buy stack base on Symbol and number of shares
    if request.method == "POST":

        stock_symbol = request.form.get("symbol")
        numb_shares = request.form.get("shares")
        stock_info = lookup(stock_symbol)

        # Display error message if stock symbol not found
        if stock_info == None:
            return apology("Stock symbol not found", 400)

        # Display error message if user input is numeric number
        if numb_shares.isnumeric():
            pass
        else:
            return apology("Invalid number of shares", 400)

        # Display error message if number of shares are negative
        if int(numb_shares) < 1:
            return apology("Invalid number of shares", 400)

        # Get live pricing to update in html template
        name = stock_info["name"]
        price = stock_info["price"]
        symbol = stock_info["symbol"]
        date = datetime.datetime.now()
        buy = "buy"

        # Display price and ask users confirmation to proceed with purchase
        amount = price * int(numb_shares)

        # Retrieving the available balance in users account
        ava_funds = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

        # Display error message if balance of user is insuffient
        bal_min_purch = int(ava_funds[0]["cash"]) - amount
        if bal_min_purch <= 0:
             return apology("Insufficient Funds for Purchase", 403)

        # Minus USD amount for shares purchase from wallet in user table
        db.execute("UPDATE users SET cash=? WHERE id=?", bal_min_purch, session["user_id"])

        # Update share register with purchase made by user
        name_exist = db.execute("SELECT number FROM share_register WHERE symbol=? AND user_id=?", symbol, session["user_id"])

        # Check if user already owns particular share to avoid adding multiple lines of same share
        if len(name_exist) != 0:
            number = int(name_exist[0]["number"]) + int(numb_shares)
            db.execute("UPDATE share_register SET number=?, price=?, value=? WHERE symbol =?", number, price, amount, stock_symbol)
        else:
            db.execute("INSERT INTO share_register (name, symbol, number, price, value, user_id) VALUES (?, ?, ?, ?, ?,?)", name, symbol, numb_shares, price, amount, session["user_id"])

        # Update history page with transaction by user
        db.execute("INSERT INTO trn_history (trn_date, numb_shares, buy_sell, trn_price, trn_value, name, symbol, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", date, numb_shares, buy, price, amount, name, symbol, session["user_id"])

        return render_template("buy.html", name=name, price=usd(price), symbol=symbol, amount=usd(amount), balance=usd(bal_min_purch))


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    if request.method == "GET":
        history = db.execute("SELECT * FROM trn_history WHERE user_id=?", session["user_id"])

        return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "GET":
        return render_template("quote.html")

    # Get stock price from information submitted by user
    if request.method == "POST":

        quote_symbol = request.form.get("symbol")

        # Display error message if stock symbol empty
        if quote_symbol == None:
            return apology("No stock symbol submitted", 400)

        stock_info = lookup(quote_symbol)

        # Display error message if stock symbol not found
        if stock_info == None:
            return apology("Stock symbol does not exist", 400)

        # Display stock information on Quote screen
        name = stock_info["name"]
        price = usd(stock_info["price"])
        symbol = stock_info["symbol"]

        return render_template("quote.html", name=name, price=price, symbol=symbol)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    user_name = request.form.get("username")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not user_name:
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 400)

        # Ensure confirmation password was submitted
        elif not confirmation:
            return apology("must provide confirmation password", 400)

        # Ensure password and confirmation password is a match
        elif password != confirmation:
            return apology("password and confirmation password not a match", 400)

        # Check if user name already exist
        existing = db.execute("SELECT username from users WHERE username = ?", user_name)
        if len(existing) == 1:
            return apology("User name already taken", 400)

        hash_password = generate_password_hash(password)

        # Query database for username
        db.execute("INSERT INTO users (username, hash) VALUES (?,?)", user_name, hash_password)

        session["user_id"] = user_name
        # Redirect user to login page
        return redirect("/login")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # Request information from database that will be needed during the sell process
    share_register = db.execute("Select certificate_numb, symbol, number FROM share_register WHERE user_id = ?", session["user_id"])

    share_list = []
    if request.method == "GET":

        # Create list of shares owned by user
        for share in share_register:
            share_list.append(share["symbol"])

        return render_template("sell.html", share_list=share_list)

    if request.method == "POST":

        stock_symbol = request.form.get("symbol")
        sell_shares = int(request.form.get("shares"))

        # Get existing information of shares held by users
        numb_shares = 0
        certf_numb = []
        for share in share_register:
            if share["symbol"] == stock_symbol:
                numb_shares += share["number"]
                certf_numb.append(share["certificate_numb"])

        # Check if shares are owned by user
        if numb_shares == 0:
            return apology("Stock symbol was not found in your share register!", 400)

        # Check if valid number of shares to sell have been submitted by users
        if sell_shares < 1:
            return apology("Number of shares to sell is unvalid", 400)

        # Check if user has sufficient shares to make sale
        if numb_shares < sell_shares:
            return apology("Stock owned are less than the amount you want to sell", 400)
        else:
            min_sold = numb_shares - sell_shares
            db.execute("UPDATE share_register SET number=? WHERE certificate_numb = ?", min_sold, certf_numb)

        # Get live price information to update in database and html page
        live_price = lookup(stock_symbol)
        price = live_price["price"]
        name = live_price["name"]
        symbol = live_price["symbol"]
        amount = price * sell_shares
        date = datetime.datetime.now()
        sell = "sell"

        cur_cash_bal = db.execute("SELECT cash FROM users WHERE id=?", session["user_id"])

        new_cash_bal = int(cur_cash_bal[0]["cash"]) + amount

        # Update cash balance on user table after transaction completed
        db.execute("UPDATE users SET cash=? WHERE id=?", new_cash_bal, session["user_id"])

        # Update history page with transaction by user
        db.execute("INSERT INTO trn_history (trn_date, numb_shares, buy_sell, trn_price, trn_value, name, symbol, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", date, sell_shares, sell , price, amount, name, symbol, session["user_id"])

        return render_template("sell.html", name=name, price=usd(price), symbol=symbol, amount=usd(amount), balance=usd(new_cash_bal))


@app.route("/markets")
@login_required
def markets():
    """Show market overview"""

    if request.method == "GET":
        return render_template("markets.html")
