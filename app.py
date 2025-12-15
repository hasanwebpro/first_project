from flask import Flask, request, jsonify, render_template

from automata.fa.dfa import DFA
from datetime import datetime

app = Flask(__name__)

# ---------------------------------------
# 1. DFA VALIDATION (DIGITS + LENGTH) according to Official ISO/IEC 7812 standard
# ---------------------------------------

def dfa_validate_card_number(number):
    # States: 0..19 = digit count, -1 = dead state
    states = set(range(20)) | {-1}

    # Alphabet: digits only
    alphabet = set('0123456789') # {'0','1','2','3','4','5','6','7','8','9'}

    # Transition function
    transitions = {}

    for state in range(20): # total 20 states q0 till q19
        transitions[state] = {} # assign another dictionary
        for d in alphabet:
            transitions[state][d] = state + 1 if state < 19 else -1

    # Dead state transitions
    transitions[-1] = {d: -1 for d in alphabet}

    # Create DFA
    dfa = DFA(
        states=states,
        input_symbols=alphabet,
        transitions=transitions,
        initial_state=0,
        final_states={13, 14, 15, 16, 17, 18, 19}
    )

    # Run DFA
    return dfa.accepts_input(number)

# ---------------------------------------
# 2. DETECT CARD ISSUER
# ---------------------------------------
def detect_card_issuer(number):
    number = str(number)
    length = len(number)
    
    if number.startswith("4") and (length == 13 or length == 16 or length == 19):
        return "Visa"
    elif number.startswith(("51", "52", "53", "54", "55")) and length == 16:
        return "MasterCard"
    elif number.startswith(("34", "37")) and length == 15:
        return "American Express"
    elif (number.startswith("6011") or number.startswith("65")) and length == 16:
        return "Discover"
    else:
        return "Unknown"


# ---------------------------------------
# 3. CVV VALIDATION
# ---------------------------------------
def validate_cvv(cvv, issuer):
    cvv = str(cvv)
    
    if not cvv.isdigit():
        return False
    
    if issuer == "American Express":
        return len(cvv) == 4
    else:
        return len(cvv) == 3


# ---------------------------------------
# 4. EXPIRY DATE VALIDATION
# ---------------------------------------
def validate_expiry(expiry):
    # Check format MM/YY
    if len(expiry) != 5 or expiry[2] != '/':
        return False
    
    month_part = expiry[:2]
    year_part = expiry[3:]
    
    if not (month_part.isdigit() and year_part.isdigit()):
        return False
    
    month = int(month_part)
    year = int("20" + year_part) 
    
    if month < 1 or month > 12:
        return False
    
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
    if not (3 <= len(name) <= 40):
        return False
    
    for char in name:
        if not (char.isalpha() or char == ' '):
            return False
    return True


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
            result["card_number_valid"] = False
            result["errors"].append("Invalid card number format.")
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
