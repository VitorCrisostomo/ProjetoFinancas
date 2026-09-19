from flask import request, jsonify
from config import app, db
from backend.repository.user_repository import UserRepository
from backend.validators.email_validator import is_valid_email

@app.route("/contacts", methods=["GET"])
def get_contacts():
    contacts = User.query.all()
    json_contacts = list(map(lambda x: x.to_json(), contacts))
    return jsonify({"contacts": json_contacts})

@app.route("/create_user", methods=["POST"])
def create_user():
    first_name = request.json.get("firstName")
    last_name = request.json.get("lastName")
    email = request.json.get("email")

    if not is_valid_email(email):
        return(
            jsonify({"message": "Your email must be valid"}),
            400,
        )

    if not first_name or not last_name or not email:
        return (
            jsonify({"message": "You must include a first name, last name and email"}),
            400,
        )

    new_contact = User(first_name=first_name, last_name=last_name, email=email)
    try:
        db.session.add(new_contact)
        db.session.commit()
    except Exception as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"message": "User created!"}), 201

@app.route("/update_contact/<int:user_id>", methods=["PATCH"])
def update_contact(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.json

    first_name = data.get("firstName")
    last_name = data.get("lastName")
    email = data.get("email")

    if not first_name or not last_name or not email:
        return (
            jsonify({"message": "You must include a first name, last name and email"}),
            400,
        )    

    user.first_name = first_name
    user.last_name = last_name
    user.email = email

    db.session.commit()

    return jsonify({"message": "User updated"}), 200

@app.route("/delete_contact/<int:user_id>", methods=["DELETE"])
def delete_contact(user_id):
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "User deleted!"}), 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
