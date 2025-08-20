import os
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect

from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Person, Planet, Favorite, ensure_initial_user_if_empty

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url.replace(
        "postgres://", "postgresql://")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/starwars.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

with app.app_context():
    insp = inspect(db.engine)
    if "users" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("users")}
        if "email" in cols:
            ensure_initial_user_if_empty()


@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code


@app.route("/")
def sitemap():
    return generate_sitemap(app)


def get_json_or_400() -> dict:
    data = request.get_json(silent=True)
    if data is None:
        raise APIException("Expected application/json body", status_code=400)
    return data


def get_current_user() -> User:
    header_user_id = request.headers.get("X-User-Id")
    if header_user_id:
        try:
            uid = int(header_user_id)
        except ValueError:
            raise APIException("X-User-Id must be an integer", status_code=400)
        user = db.session.get(User, uid)
        if not user:
            raise APIException(
                f"User with id={uid} not found", status_code=404)
        return user

    user = db.session.query(User).order_by(User.id.asc()).first()
    if not user:
        raise APIException(
            "No users found. Create one via admin/migration.", status_code=400)
    return user


@app.route("/people", methods=["GET"])
def list_people():
    people = db.session.query(Person).order_by(Person.id.asc()).all()
    return jsonify([p.serialize() for p in people]), 200


@app.route("/people/<int:people_id>", methods=["GET"])
def get_person(people_id: int):
    person = db.session.get(Person, people_id)
    if not person:
        raise APIException(
            f"Person with id={people_id} not found", status_code=404)
    return jsonify(person.serialize()), 200


@app.route("/people", methods=["POST"])
def create_person():
    data = get_json_or_400()
    if not data.get("name"):
        raise APIException("Field 'name' is required", status_code=400)

    person = Person(
        name=data["name"],
        height=data.get("height"),
        mass=data.get("mass"),
        birth_year=data.get("birth_year"),
        hair_color=data.get("hair_color"),
        skin_color=data.get("skin_color"),
        eye_color=data.get("eye_color"),
        gender=data.get("gender"),
    )
    db.session.add(person)
    db.session.commit()
    return jsonify(person.serialize()), 201


@app.route("/people/<int:people_id>", methods=["PUT"])
def update_person(people_id: int):
    person = db.session.get(Person, people_id)
    if not person:
        raise APIException(
            f"Person with id={people_id} not found", status_code=404)

    data = get_json_or_400()
    allowed = {"name", "height", "mass", "birth_year",
               "hair_color", "skin_color", "eye_color", "gender"}
    for k, v in data.items():
        if k in allowed:
            setattr(person, k, v)

    db.session.commit()
    return jsonify(person.serialize()), 200


@app.route("/people/<int:people_id>", methods=["DELETE"])
def delete_person(people_id: int):
    person = db.session.get(Person, people_id)
    if not person:
        raise APIException(
            f"Person with id={people_id} not found", status_code=404)
    db.session.delete(person)  # cascades remove favorites
    db.session.commit()
    return jsonify({"msg": "Person deleted"}), 200


@app.route("/planets", methods=["GET"])
def list_planets():
    planets = db.session.query(Planet).order_by(Planet.id.asc()).all()
    return jsonify([p.serialize() for p in planets]), 200


@app.route("/planets/<int:planet_id>", methods=["GET"])
def get_planet(planet_id: int):
    planet = db.session.get(Planet, planet_id)
    if not planet:
        raise APIException(
            f"Planet with id={planet_id} not found", status_code=404)
    return jsonify(planet.serialize()), 200


@app.route("/planets", methods=["POST"])
def create_planet():
    data = get_json_or_400()
    if not data.get("name"):
        raise APIException("Field 'name' is required", status_code=400)

    planet = Planet(
        name=data["name"],
        diameter=data.get("diameter"),
        rotation_period=data.get("rotation_period"),
        orbital_period=data.get("orbital_period"),
        gravity=data.get("gravity"),
        population=data.get("population"),
        surface_water=data.get("surface_water"),
        climate=data.get("climate"),
        terrain=data.get("terrain"),
    )
    db.session.add(planet)
    db.session.commit()
    return jsonify(planet.serialize()), 201


@app.route("/planets/<int:planet_id>", methods=["PUT"])
def update_planet(planet_id: int):
    planet = db.session.get(Planet, planet_id)
    if not planet:
        raise APIException(
            f"Planet with id={planet_id} not found", status_code=404)

    data = get_json_or_400()
    allowed = {"name", "diameter", "rotation_period", "orbital_period",
               "gravity", "population", "surface_water", "climate", "terrain"}
    for k, v in data.items():
        if k in allowed:
            setattr(planet, k, v)

    db.session.commit()
    return jsonify(planet.serialize()), 200


@app.route("/planets/<int:planet_id>", methods=["DELETE"])
def delete_planet(planet_id: int):
    planet = db.session.get(Planet, planet_id)
    if not planet:
        raise APIException(
            f"Planet with id={planet_id} not found", status_code=404)
    db.session.delete(planet)
    db.session.commit()
    return jsonify({"msg": "Planet deleted"}), 200


@app.route("/users", methods=["GET"])
def list_users():
    users = db.session.query(User).order_by(User.id.asc()).all()
    return jsonify([u.serialize() for u in users]), 200


@app.route("/users/favorites", methods=["GET"])
def list_user_favorites():
    user = get_current_user()
    favs = db.session.query(Favorite).filter(
        Favorite.user_id == user.id).order_by(Favorite.id.asc()).all()
    return jsonify([f.serialize() for f in favs]), 200


@app.route("/favorite/planet/<int:planet_id>", methods=["POST"])
def add_favorite_planet(planet_id: int):
    user = get_current_user()
    planet = db.session.get(Planet, planet_id)
    if not planet:
        raise APIException(
            f"Planet with id={planet_id} not found", status_code=404)

    fav = Favorite(user_id=user.id, item_type="planet",
                   planet_id=planet_id, person_id=None)
    db.session.add(fav)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise APIException(
            "Favorite already exists for this planet", status_code=409)
    return jsonify(fav.serialize()), 201


@app.route("/favorite/people/<int:people_id>", methods=["POST"])
def add_favorite_person(people_id: int):
    user = get_current_user()
    person = db.session.get(Person, people_id)
    if not person:
        raise APIException(
            f"Person with id={people_id} not found", status_code=404)

    fav = Favorite(user_id=user.id, item_type="person",
                   person_id=people_id, planet_id=None)
    db.session.add(fav)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise APIException(
            "Favorite already exists for this person", status_code=409)
    return jsonify(fav.serialize()), 201


@app.route("/favorite/planet/<int:planet_id>", methods=["DELETE"])
def delete_favorite_planet(planet_id: int):
    user = get_current_user()
    fav = db.session.query(Favorite).filter_by(
        user_id=user.id, item_type="planet", planet_id=planet_id
    ).first()
    if not fav:
        raise APIException(
            "Favorite planet not found for current user", status_code=404)
    db.session.delete(fav)
    db.session.commit()
    return jsonify({"msg": "Favorite planet removed"}), 200


@app.route("/favorite/people/<int:people_id>", methods=["DELETE"])
def delete_favorite_person(people_id: int):
    user = get_current_user()
    fav = db.session.query(Favorite).filter_by(
        user_id=user.id, item_type="person", person_id=people_id
    ).first()
    if not fav:
        raise APIException(
            "Favorite person not found for current user", status_code=404)
    db.session.delete(fav)
    db.session.commit()
    return jsonify({"msg": "Favorite person removed"}), 200


@app.route("/user", methods=["GET"])
def get_current_user_endpoint():
    user = get_current_user()
    return jsonify(user.serialize()), 200


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=PORT, debug=False)
