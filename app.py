from flask import Flask, request, jsonify, render_template

import re
from datetime import datetime

app = Flask(__name__)

# ---------------------------------------
# 1. DFA VALIDATION (DIGITS + LENGTH)
# ---------------------------------------
def dfa_validate_card_number(number):
    for ch in number:
        if not ch.isdigit():
            return False
    return 13 <= len(number) <= 19


# ---------------------------------------
# 2. DETECT CARD ISSUER
# ---------------------------------------
def detect_card_issuer(number):
    patterns = {
        "Visa": "^4[0-9]{12}(?:[0-9]{3})?$",
        "MasterCard": "^5[1-5][0-9]{14}$",
        "American Express": "^3[47][0-9]{13}$",
        "Discover": "^6(?:011|5[0-9]{2})[0-9]{12}$"
    }
    for issuer, pattern in patterns.items():
        if re.fullmatch(pattern, number):
            return issuer
    return "Unknown"


# ---------------------------------------
# 3. CVV VALIDATION
# ---------------------------------------
def validate_cvv(cvv, issuer):
    if issuer == "American Express":
        return re.fullmatch(r"\d{4}", cvv) != None
    return re.fullmatch(r"\d{3}", cvv) != None


# ---------------------------------------
# 4. EXPIRY DATE VALIDATION
# ---------------------------------------
def validate_expiry(expiry):
    if re.fullmatch(r"(0[1-9]|1[0-2])/[0-9]{2}", expiry) == None:
        return False

    month, year = expiry.split("/")
    month = int(month)
    year = int("20" + year)

    now = datetime.now()
    if year > now.year:
        return True
    if year == now.year and month >= now.month:
        return True
    return False


# ---------------------------------------
# 5. NAME VALIDATION
# ---------------------------------------
def validate_name(name):
    return re.fullmatch(r"[A-Za-z ]{3,40}", name) != None


# ---------------------------------------
# 6. MASTER VALIDATOR
# ---------------------------------------
def validate_card_input(card_number, cvv, expiry, name):
    result = {
        "card_number_valid": False,
        "issuer": None,
        "cvv_valid": False,
        "expiry_valid": False,
        "name_valid": False,
        "overall_status": False,
        "errors": []
    }

    # Card number
    if dfa_validate_card_number(card_number):
        result["card_number_valid"] = True
        result["issuer"] = detect_card_issuer(card_number)
        if result["issuer"] == "Unknown":
            result["errors"].append("Card issuer pattern not recognized.")
    else:
        result["errors"].append("Invalid card number format.")

    # CVV
    if validate_cvv(cvv, result["issuer"]):
        result["cvv_valid"] = True
    else:
        result["errors"].append("Invalid CVV format.")

    # Expiry
    if validate_expiry(expiry):
        result["expiry_valid"] = True
    else:
        result["errors"].append("Invalid or expired expiry date.")

    # Name
    if validate_name(name):
        result["name_valid"] = True
    else:
        result["errors"].append("Invalid cardholder name.")

    # Final status
    if result["card_number_valid"] and result["cvv_valid"] and result["expiry_valid"] and result["name_valid"]:
        result["overall_status"] = True

    return result


# ------------------------------------------------
# 7. FLASK ROUTE FOR FRONTEND INTEGRATION
# ------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/validate-card", methods=["POST"])
def validate_card():
    data = request.json
    card_number = data.get("card_number", "")
    cvv = data.get("cvv", "")
    expiry = data.get("expiry", "")
    name = data.get("name", "")
    result = validate_card_input(card_number, cvv, expiry, name)
    return jsonify(result)

@app.route("/test")
def test():
    sample_data = {
        "card_number": "4111111111111111",
        "cvv": "123",
        "expiry": "12/25",
        "name": "John Doe"
    }
    result = validate_card_input(
        sample_data["card_number"],
        sample_data["cvv"],
        sample_data["expiry"],
        sample_data["name"]
    )
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)