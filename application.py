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

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    db = SQL("sqlite:///finance.db")

    rows_list = db.execute("SELECT symbol, shares FROM portfolios WHERE id=:id", id=session['user_id'])
    user = db.execute("SELECT * FROM users WHERE id=:id", id=session['user_id'])
    cash = user[0]['cash']
    total_cash_value = 0
    if len(rows_list) == 0: 
        print('len or row list is zero')
        return render_template('index.html', cash=usd(cash))
    for row in rows_list:
        stock_info = lookup(row['symbol'])
        current_price_float = stock_info['price']
        row['stock_name'] = stock_info['name']
        row['current_price'] = usd(stock_info['price'])
        total_price_float = current_price_float * float(row['shares'])
        row['total_stock_value'] = usd(total_price_float)
        total_cash_value += total_price_float
    total_cash_value += cash
    return render_template('index.html', rows=rows_list, cash=usd(cash), total_cash_value=usd(total_cash_value))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    db = SQL("sqlite:///finance.db")

    if request.method == "GET":
        return render_template('buy.html')
    else:
        
        # Validate user inputs
        symbol = request.form.get('symbol').upper()
        if not symbol:
            return apology('You must provide a stock symbol')
        shares = request.form.get('shares')
        if not shares:
            return apology('You must provide a valid number of shares')
        shares_to_buy = int(request.form.get('shares'))
        if shares_to_buy <= 0:
            return apology('You must provide a valid number of shares')
        quote = lookup(symbol)
        if quote == None:
            return apology('Invalid stock symbol')
        stock_price = (quote['price'])
        total_cost = stock_price * shares_to_buy

        # Query database to get the amount of cash user has available
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
        cash_available = rows[0]['cash']

        # Get the amount of cash after the transaction
        updated_cash = cash_available - total_cost

        #Make sure there is enough cash to cover the purchase
        if total_cost < cash_available:

            # Everythings OK, 1.update cash 2.update portfolios table 3.update history table
            # Update cash in users table
            db.execute("UPDATE users SET cash = :updated_cash WHERE id=:id", updated_cash=updated_cash, id=session["user_id"])
            
            # update portfolios table
            rows = db.execute("SELECT * FROM portfolios WHERE id=:id AND symbol=:symbol", id=session["user_id"], symbol=symbol)
            if len(rows) == 0:
                db.execute("INSERT INTO portfolios (id, symbol, shares) VALUES (:id, :symbol, :shares)", \
                           id=session["user_id"], symbol=symbol, shares=shares_to_buy)
            else:
                db.execute("UPDATE portfolios SET shares = shares + :shares WHERE id=:id AND symbol=:symbol", shares=shares_to_buy, \
                           id=session['user_id'], symbol=symbol)
            
            # update history table
            db.execute("INSERT INTO history (id, symbol, shares, price) VALUES \
                       (:id, :symbol, :shares, :price)", id=session["user_id"], shares=shares_to_buy, price=stock_price, symbol=symbol) 
            
            # flash message
            flash("Shares Bought!")
            return redirect('/')
        else:
            return apology("You have insufficient funds to complete the purchase")


@app.route("/history")
@login_required
def history():
    db = SQL("sqlite:///finance.db")

    # query database for history table
    history_list = db.execute('SELECT * FROM history WHERE id=:id', id=session['user_id'])
    if len(history_list) == 0:
        message = "No transaction history"
    else:
        message = ''

    # # lookup name of symbol and add to list
    # for row in history_list:
    #     quote = lookup(row['symbol'])
    #     if quote == None:
    #         return apology('Invalid stock symbol in history')
    #     row['name'] = quote['name']
    return render_template('history.html', history_list = history_list, message=message)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    db = SQL("sqlite:///finance.db")

    # Forget any user_id
    session.clear()

    # Passes in the image for background only on register and login
    home_index = "home_index"
    
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

        flash('You were successfully logged in')
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html", home_index=home_index)


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # flash message
    flash('Logged Out')
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
    db = SQL("sqlite:///finance.db")
    # Passes in the image for background only on register and login
    home_index = "home_index"

    if request.method == "GET":
        return render_template("register.html", home_index=home_index)
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

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        # Make sure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return apology("invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Add flash message
        flash('Registered!')
        # Redirect to home page
        return redirect('/')

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    db = SQL("sqlite:///finance.db")

    if request.method == "GET":
       return render_template('sell.html')
    else: 
        symbol = request.form.get('symbol').upper()
        if not symbol:
            return apology('Need to enter a stock symbol')
        
        # Use helper function to get quote
        quote = lookup(symbol)

        # Check if lookup failed
        if quote == None:
            return apology("Invalid symbol")
        
        # Get the number of shares inputted by user
        shares = request.form.get('shares')
        if not shares:
            return apology('Need to enter a number of shares')

        shares_to_sell = int(shares)
        if shares_to_sell <= 0:
            return apology('Need to enter valid number of shares')

        # Check to see if user has the stock in portfolio and enough shares to sell
        shares_already_list = db.execute('SELECT shares FROM portfolios WHERE id=:id AND symbol=:symbol', id=session['user_id'], symbol=symbol)
        if len(shares_already_list) == 0:
            return apology('stock is not in portfolio')
        shares_already = shares_already_list[0]['shares']
        
        if shares_to_sell > shares_already:
            return apology('cannot sell more shares than you own')
        
        updated_shares = shares_already - shares_to_sell

        # Get current price of stock
        price = quote['price']

        # Update the portfolios table
        # If shares = 0, delete row
        if updated_shares == 0:
            db.execute('DELETE from portfolios WHERE id=:id AND symbol=:symbol', id=session['user_id'], symbol=symbol)
        else:
            db.execute('UPDATE portfolios SET shares = :updated_shares WHERE id=:id AND symbol=:symbol', updated_shares=updated_shares, \
                    id=session['user_id'], symbol=symbol)
        
        # Update the history table
        db.execute('INSERT INTO history (id, symbol, shares, price) VALUES (:id, :symbol, :shares, :price)',  \
                    id=session['user_id'], symbol=symbol, shares=-(shares_to_sell), price=price)
        
        # Increase in cash after selling stock
        increase_cash = price * shares_to_sell

        # Update cash in users table
        db.execute('UPDATE users SET cash=cash+:increase WHERE id=:id', increase=increase_cash, id=session['user_id'])
        
        # Add flash message
        flash('Shares Sold!')

        return redirect('/')

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


@app.route('/changepw', methods=["POST", "GET"])
@login_required
def changepw():
    if request.method == "GET":
        return render_template('changepw.html')
    else:
        db = SQL("sqlite:///finance.db")

        # Validate user inputs
        cur_pw = request.form.get('cur_pw')
        new_pw = request.form.get('new_pw')
        confirm_pw = request.form.get('confirm_pw')
        if not cur_pw:
            return apology('You must enter your password', 403)
        elif not new_pw:
            return apology('You must enter a new password', 403)
        elif not confirm_pw:
            return apology('You must re-enter your password', 403)
        elif new_pw != confirm_pw:
            return apology('Passwords do not match')
        print(new_pw)
        user_list = db.execute("SELECT * FROM users WHERE id=:id", id=session['user_id'])
        
        # Vheck if the current passwords match
        if not check_password_hash(user_list[0]["hash"], cur_pw):
            return apology("invalid current password", 403)

        # Query db and update to new password
        db.execute("UPDATE users SET hash=:hash WHERE id=:id", hash=generate_password_hash(new_pw), id=session['user_id'])
        
        flash('Password Changed')
        return redirect('/')
        
@app.route('/deposit', methods=["GET", "POST"])
@login_required
def deposit():
    db = SQL("sqlite:///finance.db")
    if request.method == "GET":
        return render_template('deposit.html')
    else:
        cash_list = db.execute("SELECT cash FROM users WHERE id=:id", id=session['user_id'])
        add_funds = int(request.form.get('add_funds'))
        if not add_funds or add_funds <= 0:
            return apology('Invalid Amount')
        db.execute('UPDATE users SET cash= cash + :add_funds WHERE id=:id', add_funds=add_funds, id=session['user_id'])
        flash("Added new funds")
        return redirect('/')