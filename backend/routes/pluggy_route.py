@pluggy_routes.route("/pluggy/transactions", methods=["GET"])
def get_transactions():
    transactions = pluggy_service.get_transactions()

    return jsonify(transactions), 200