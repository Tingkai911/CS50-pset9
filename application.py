import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

import datetime
import credit # modified from pset6

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

# DONE
@app.route("/")
@login_required # user must be logged to to see the index page
def index():
    rows = db.execute("""SELECT symbol, SUM(shares) FROM accounts
                            JOIN users ON id == user_id
                            WHERE user_id == :user_id
                            AND symbol != "CASH"
                            GROUP BY symbol
                            HAVING SUM(shares) > 0""", user_id = session["user_id"])
    sum_of_shares_price = 0
    # Get the current price
    for row in rows:
        quoted = lookup(row["symbol"])
        unit_price = quoted["price"]
        total_price = float(quoted["price"])*float(row["SUM(shares)"])
        row["name"] = quoted["name"]
        row["current_price"] = unit_price
        row["total_price"] = round(total_price, 2)
        sum_of_shares_price += total_price

    # check how much cash the user has
    funds = db.execute("SELECT cash FROM users WHERE id == :user_id", user_id = session["user_id"])
    cash = round(funds[0]["cash"], 2)

    total_value = round(cash + sum_of_shares_price, 2)
    return render_template("index.html", rows = rows, cash = cash, total_value = total_value)

#DONE
@app.route("/addfunds", methods=["GET", "POST"])
@login_required
def addFunds():
    if request.method == "GET":
        return render_template("addfunds.html")
    else:
        credit_card_number = int(request.form.get("number"))
        amount = float(request.form.get("amount"))

        # check if the credit card number is valid
        is_valid = credit.luhn(credit_card_number)
        if not is_valid:
            return apology("Invalid Credit Card.")

        funds = db.execute("SELECT cash FROM users WHERE id == :user_id", user_id = session["user_id"])
        cash = float(funds[0]["cash"])

        cash = cash + amount
        # update the users table
        db.execute("UPDATE users SET cash = :cash WHERE id == :user_id", cash = cash, user_id = session["user_id"])

        date_time = datetime.datetime.now()
        date_time = date_time.strftime("%Y-%m-%d %H:%M:%S")

        # update the accounts table
        db.execute("""INSERT INTO accounts (user_id, symbol, date_time, total_price)
                        VALUES (:user_id, :symbol, :date_time, :total_price)""",
                        user_id = session["user_id"], symbol = "CASH",
                        date_time = date_time, total_price = amount)

        flash("Funds Added.")
        return redirect("/")


# DONE
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        quoted = lookup(symbol)
        if not quoted:
            return apology("Invalid Symbol.")
        if not shares:
            return apology("Must buy minimum 1 share.")
        #check if the user has enough cash to buy the stock
        funds = db.execute("SELECT cash FROM users WHERE id == :user_id", user_id = session["user_id"])
        total_price = float(quoted["price"])*float(shares)
        cash = float(funds[0]["cash"])
        # user cannot afford
        if total_price > cash:
            return apology("Can't Afford.")

        # update the remaining cash in users table
        cash = cash - total_price
        db.execute("UPDATE users SET cash = :cash WHERE id == :user_id", cash = cash, user_id = session["user_id"])

        date_time = datetime.datetime.now()
        date_time = date_time.strftime("%Y-%m-%d %H:%M:%S")

        # update the accounts table
        db.execute("INSERT INTO accounts VALUES (:user_id, :symbol, :shares, :date_time, :unit_price, :total_price)",
                    user_id = session["user_id"], symbol = symbol,
                    shares = shares, date_time = date_time,
                    unit_price = quoted["price"], total_price = total_price)
        flash("Bought.")
        return redirect("/")

    return apology("Buy is not working.")

# DONE
@app.route("/history")
@login_required
def history():
    rows = db.execute("""SELECT * FROM accounts
                            JOIN users ON id == user_id
                            WHERE user_id == :user_id""", user_id = session["user_id"])
    return render_template("history.html", rows = rows)


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

# DONE
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("symbol")
        quoted = lookup(symbol)
        if not quoted:
            return apology("Invalid Symbol")
        return render_template("quoted.html",name=quoted["name"], symbol=quoted["symbol"], price=quoted["price"])

    return apology("Quote is not working.")


# DONE
@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changePassword():
    if request.method == "GET":
        return render_template("changepassword.html")
    else:
        old_password = request.form.get("old_password")
        if not old_password:
            return apology("Input current password.")

        # query database for user_id
        rows = db.execute("SELECT hash FROM users WHERE id = :user_id", user_id=session["user_id"])
        # ensure current password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], old_password):
            return apology("Invalid password")

        new_password = request.form.get("new_password")
        if not new_password:
            return apology("Please make a new password.")

        confirm_password = request.form.get("confirm_password")
        if new_password != confirm_password:
            return apology("The password didn't match")

        # update database
        password_hash = generate_password_hash(new_password)
        db.execute("UPDATE users SET hash = :password_hash WHERE id = :user_id", user_id=session["user_id"], password_hash = password_hash)

        flash("Password Changed")
        return redirect("/")



# DONE
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        if not username:
            return apology("You must provide a Username.")
        # checks if the username is already taken by other users
        name = db.execute("SELECT username FROM users WHERE username == :username", username=username)
        if len(name)>=1:
            return apology("This username is already taken.")

        password = request.form.get("password")
        if not password:
            return apology("You must provide a password.")

        # user must type in the same password twice to successfully register
        confirm_password = request.form.get("confirm_password")
        if not confirm_password or password != confirm_password:
            return apology("The password didn't match.")

        password_hash = generate_password_hash(password)

        # add user to database
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :password_hash)", username=username, password_hash=password_hash)

        # login user automatically and remember session
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)
        session["user_id"] = rows[0]["id"]

        # redirect to index()
        return redirect("/")

    return apology("Register is not working.")

# DONE
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        # load what are the shares that the current user owns
        rows = db.execute("""SELECT symbol FROM accounts
                                JOIN users ON id == user_id
                                WHERE user_id == :user_id
                                AND symbol != "CASH"
                                GROUP BY symbol
                                HAVING SUM(shares) > 0""", user_id = session["user_id"])
        return render_template("sell.html", rows = rows)
    else:
        symbol = request.form.get("symbol").upper()
        shares = request.form.get("shares")
        quoted = lookup(symbol)
        if not quoted:
            return apology("Invalid Symbol.")
        if not shares:
            return apology("Must sell minimum 1 share.")

        # check how many shares the user owns
        rows = db.execute("""SELECT SUM(shares) FROM accounts
                                JOIN users ON id == user_id
                                WHERE user_id == :user_id
                                AND symbol == :symbol
                                GROUP BY symbol""", user_id = session["user_id"], symbol = symbol)
        current_shares = float(rows[0]["SUM(shares)"])
        shares = float(shares)
        if shares > current_shares:
            return apology("You don't have so much shares.")

        total_sell_price = float(quoted["price"])*float(shares)

        # look up how much cash the user has
        funds = db.execute("SELECT cash FROM users WHERE id == :user_id", user_id = session["user_id"])
        cash = float(funds[0]["cash"])

        # update the remaining cash in users table
        cash = cash + total_sell_price
        db.execute("UPDATE users SET cash = :cash WHERE id == :user_id", cash = cash, user_id = session["user_id"])

        date_time = datetime.datetime.now()
        date_time = date_time.strftime("%Y-%m-%d %H:%M:%S")

        # update the accounts table
        db.execute("INSERT INTO accounts VALUES (:user_id, :symbol, :shares, :date_time, :unit_price, :total_price)",
                    user_id = session["user_id"], symbol = symbol,
                    shares = -shares, date_time = date_time,
                    unit_price = -float(quoted["price"]), total_price = -total_sell_price)
        flash("Sold.")
        return redirect("/")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
