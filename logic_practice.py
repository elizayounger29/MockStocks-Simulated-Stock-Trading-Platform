from helpers import apology, lookup
from cs50 import SQL
from flask import render_template
session = {}
session["user_id"] = 1

method = "POST"
# symbol = 'googl'

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

def input_check(shares):
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


if __name__ == "__main__":
    # Example usage of the decorated function
    pass



