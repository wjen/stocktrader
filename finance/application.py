import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    db = SQL("sqlite:///finance.db")

    rows = db.execute("SELECT symbol, shares, cash FROM portfolios JOIN users ON users.id = portfolios.id WHERE users.id=:id", id=session['user_id'])
    for row in rows:
        stock_info = lookup(row['symbol'])
        row['current_price'] = f"{stock_info['price']}"
        row['total_value'] = f"{float(row['current_price']) * float(row['shares']):,.2f}"
    rows[0]['cash'] = f"{rows[0]['cash']:,.2f}"
    return render_template('index.html', rows=rows)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template('buy.html')
    else:
        symbol = request.form.get('symbol').upper()
        if not symbol:
            return apology('You must provide a stock symbol')
        shares_to_buy = int(request.form.get('shares'))
        if not shares_to_buy:
            return apology('You must provide a valid number of shares')
        quote = lookup(symbol)
        if quote == None:
            return apology('Invalid stock symbol')
        stock_price = float(quote['price'])
        total_cost = stock_price * shares_to_buy
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        cash_available = rows[0]['cash']
        cash_remaining = cash_available - total_cost
        if total_cost < cash_available:

            # Everythings OK, 1.update cash 2.update portfolios table 3.update history table
            # Update cash in users table
            db.execute("UPDATE users SET cash = :cash_remaining WHERE id=:id", cash_remaining=cash_remaining, id=session["user_id"])
            
            # update portfolios table
            rows = db.execute("SELECT * FROM portfolios WHERE id=:id AND symbol=:symbol", id=session["user_id"], symbol=symbol)
            if len(rows) == 0:
                db.execute("INSERT INTO portfolios (id, symbol, shares) VALUES (:id, :symbol, :shares)", \
                           id=session["user_id"], symbol=symbol, shares=shares_to_buy)
            else:
                db.execute("UPDATE portfolios SET shares = shares + :shares", shares=shares_to_buy)
            
            # update history table
            db.execute("INSERT INTO history (id, symbol, shares, price) VALUES \
                       (:id, :symbol, :shares, :price)", id=session["user_id"], shares=shares_to_buy, price=stock_price, symbol=symbol) 
            return redirect('/')
        else:
            return apology("You have insufficient funds to complete the purchase")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


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
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

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
    if request.method == 'GET':
        return render_template('quote.html')
    else:
        symbol = request.form.get('symbol')
        if not symbol:
            return apology('You must provide a stock symbols')
        quote = lookup(symbol)
        if quote == None:
            return apology('Could not find quote')
        quote['price'] = usd(quote['price'])
        return render_template('quoted.html', stock_info=quote)


@app.route("/register", methods=["GET", "POST"])
def register():
    
    session.clear()
    
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        if not username:
            return apology("You must provide a username")
        password = request.form.get("password")        
        if not password:
            return apology("You must provide a password")
        confirmation = request.form.get("confirmation")
        if not confirmation:
            return apology("You must provide a password")
        if confirmation != password:
            return apology("Passwords do not match")
        
        rows = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=username, hash=generate_password_hash(password))

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        # make sure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        #redirect to home page
        return redirect('/')

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
