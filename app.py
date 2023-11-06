import os
import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

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


def check(string, message):
    if string == "" or string == None or string == False:
        return apology(message)
    return


#############################   BALANCE  ################################
@app.route("/balance", methods=["GET", "POST"])
@login_required
def balance():
    username = db.execute(
        "SELECT username FROM users WHERE id = ?;", session["user_id"]
    )
    username = username[0]["username"]

    # Retrieve the current balance
    balance_result = db.execute(
        "SELECT cash FROM users WHERE id = ?", session["user_id"]
    )
    balance = balance_result[0]["cash"]

    if request.method == "POST":
        # Retrieve the raise_balance input from the form
        raise_balance = request.form.get("balance")

        # Check that raise_balance is a valid number (you can use try-except for error handling)
        try:
            raise_balance = float(raise_balance)
        except ValueError:
            return apology("Invalid input for raising balance")

        if raise_balance < 0:
            return apology("You can't add a negative amount")

        # Calculate the new balance
        new_balance = balance + raise_balance

        # Update the user's balance in the database
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?;", new_balance, session["user_id"]
        )

        return redirect("/")

    return render_template("balance.html", username=username, balance=balance)


#############################   INDEX  ################################


def calculate_portfolio():
    rows = db.execute(
        "SELECT symbol, quantity, action FROM purchase_history WHERE user_id = ?;",
        session["user_id"],
    )
    portfolio = {}
    for row in rows:
        if row["symbol"] not in portfolio:  # if symbol not in portfolio
            if row["action"] == "sell":  # if sell
                return "you have a problem with your stock maths"
            portfolio[row["symbol"]] = row["quantity"]  # add stock to portfolio
        else:
            if row["action"] == "buy":
                portfolio[row["symbol"]] += row["quantity"]
            else:
                portfolio[row["symbol"]] -= row["quantity"]
    return portfolio


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if not session.get("user_id"):
        return redirect("/login")

    """Show portfolio of stocks"""
    if request.method == "POST":
        return redirect("/balance")
    # Query database for username
    username = db.execute(
        "SELECT username FROM users WHERE id = ?;", session["user_id"]
    )
    balance_result = db.execute(
        "SELECT cash FROM users WHERE id = ?", session["user_id"]
    )
    portfolio = calculate_portfolio()
    if username != None:
        username = username[0]["username"]
        balance = balance_result[0]["cash"]
        return render_template(
            "index.html", portfolio=portfolio, username=username, balance=balance
        )
    else:
        return render_template(
            "index.html", portfolio=portfolio, username="user", balance="N/A"
        )


#############################   BUY  ################################


def shares_input_check(shares):
    if isinstance(shares, tuple):
        try:
            number = str(shares[0])
            number = float(number)      # Attempt to convert the first element of the tuple to a float
            if number > 0:
                return number
        except ValueError:
            return apology("invalid input")  # Conversion to float failed
    if isinstance(shares, str):
        try:
            number = float(shares)
            if number > 0:
                return number
        except ValueError:
            return apology("invalid input")  # Conversion to float failed

    return apology("invalid input")



def cost_calculator(price, shares):
    if isinstance(shares, tuple):
        try:
            shares = str(shares[0])
            shares = float(shares)
            cost = price * shares
        except ValueError:
            return apology("invalid share input")
        return cost
    else:
        try:
            shares = float(shares)
            cost = price * shares
        except ValueError:
            return apology("invalid share input")
        return cost


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # Query database for share name and quantity. This returns a tuple
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if not symbol:
            return apology("must input stock symbol")
        # if shares is None: - this didn't work!
        if not shares:
            return apology("must input shares")

        shares = shares_input_check(shares)

        price = lookup(symbol)
        if price == None:
            return apology("invalid stock symbol, please try again")
        price = price["price"]
        # calculate price
        cost = cost_calculator(price, shares)

        # get user balance
        balance = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        balance = balance[0]["cash"]
        balance = float(balance)

        # check user has enough money
        if cost > balance:
            return apology("Not enough funds to make purchase, try again")

        # minus stock price from balance
        new_balance = balance - cost
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?;", new_balance, session["user_id"]
        )

        current_time = datetime.datetime.now()
        time = f"{current_time.year}-{current_time.month}-{current_time.day} {current_time.hour}:{current_time.minute}:{current_time.second}"

        # log purchase in purchase_history
        db.execute(
            """INSERT INTO purchase_history (user_id, symbol, quantity, price, action, time) VALUES (?, ?, ?, ?, ?, ?);""",
            session["user_id"],
            symbol,
            shares,
            cost,
            "buy",
            time,
        )

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


#############################   HISTORY  ################################


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Query database for username
    username = db.execute(
        "SELECT username FROM users WHERE id = ?;", session["user_id"]
    )
    username = username[0]["username"]

    # load purchase history
    history = db.execute(
        "SELECT purchase_id, symbol, quantity, price, action, time FROM purchase_history WHERE user_id = ?;",
        session["user_id"],
    )

    return render_template("history.html", history=history, username=username)


#############################   LOGIN  ################################


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
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


#############################   LOGOUT  ################################


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


#############################   QUOTE  ################################


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("stock symbol required, please try again")
        stock = lookup(symbol)
        if stock == None:
            return apology("invalid stock symbol, please try again")
        if stock != None:
            return render_template("quoted.html", stock=stock)
    else:
        return render_template("quote.html")


#############################   REGISTER  ################################


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            return apology("must provide username")
        # Ensure password was submitted
        if not password:
            return apology("must provide password")

        # Query database for the proposed username & password
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Ensure no duplicate username exists
        if len(rows) > 0:
            return apology("Sorry that username is already taken, please try again.")

        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Sorry those passwords don't match, please try again.")

        # Query database for username
        rows = db.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?);",
            username,
            generate_password_hash(request.form.get("password")),
        )

        # Remember which user has logged in
        # session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/login")

    else:
        return render_template("register.html")


#############################   SELL    ################################


def sell_stock_check(symbol, shares):
    portfolio = calculate_portfolio()
    if symbol not in portfolio:  # no shares in that stock
        return apology(
            "You don't own any of this stock in order to sell, please try again"
        )

    owned_shares = float(portfolio[symbol])
    shares_to_sell = float(shares)
    if owned_shares < shares_to_sell:  # not enough shares in that stock
        return apology(
            f"You don't own enough of this stock to sell {shares} shares, please try again"
        )

    return owned_shares - shares_to_sell


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        # Query database for share name and quantity
        shares = request.form.get("shares")
        symbol = request.form.get("symbol")

        if not symbol:
            return apology("must input stock symbol")
        if not shares:
            return apology("must input shares")
        shares = shares_input_check(shares)

        price = lookup(symbol)
        if price == None:
            return apology("invalid stock symbol, please try again")
        price = price["price"]

        # calculate profit
        profit = cost_calculator(price, shares)

        # get user balance
        balance = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])
        balance = balance[0]["cash"]

        # check user has enough stock in stock
        sell_stock_check(symbol, shares)
        # {"apple": 1, "nflx": 5}

        # add stock price to balance
        new_balance = balance + profit
        db.execute(
            "UPDATE users SET cash = ? WHERE id = ?;", new_balance, session["user_id"]
        )

        current_time = datetime.datetime.now()
        time = f"{current_time.year}-{current_time.month}-{current_time.day} {current_time.hour}:{current_time.minute}:{current_time.second}"

        # log purchase in purchase_history
        db.execute(
            """INSERT INTO purchase_history (user_id, symbol, quantity, price, action, time) VALUES (?, ?, ?, ?, ?, ?);""",
            session["user_id"],
            symbol,
            shares,
            profit,
            "sell",
            time,
        )

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("sell.html")
