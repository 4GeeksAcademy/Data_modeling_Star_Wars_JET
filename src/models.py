from __future__ import annotations
from typing import Optional, Literal

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import (
    String,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import sqlalchemy as sa

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"

    def serialize(self) -> dict:
        return {"id": self.id, "email": self.email}


def ensure_initial_user_if_empty() -> None:
    count = db.session.execute(sa.text("SELECT COUNT(*) FROM users")).scalar()
    if count and int(count) > 0:
        return

    insp = sa.inspect(db.engine)
    cols = {c["name"]: c for c in insp.get_columns("users")}

    values = {"email": "jose@canusee.com"}
    if "password" in cols:
        nullable = bool(cols["password"].get("nullable", True))
        if not nullable or "password" not in values:
            values["password"] = "changeme"
    if "is_active" in cols:
        values["is_active"] = True
    if "name" in cols:
        values["name"] = "Jose"

    col_list = ", ".join(values.keys())
    placeholders = ", ".join(f":{k}" for k in values.keys())
    db.session.execute(
        sa.text(f"INSERT INTO users ({col_list}) VALUES ({placeholders})"), values)
    db.session.commit()


class Person(db.Model):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mass: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    birth_year: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True)
    hair_color: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True)
    skin_color: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True)
    eye_color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    favorites: Mapped[list["Favorite"]] = relationship(
        "Favorite",
        back_populates="person",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Person id={self.id} name={self.name}>"

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "height": self.height,
            "mass": self.mass,
            "birth_year": self.birth_year,
            "hair_color": self.hair_color,
            "skin_color": self.skin_color,
            "eye_color": self.eye_color,
            "gender": self.gender,
        }


class Planet(db.Model):
    __tablename__ = "planets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    diameter: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rotation_period: Mapped[Optional[int]
                            ] = mapped_column(Integer, nullable=True)
    orbital_period: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True)
    gravity: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    population: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    surface_water: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True)
    climate: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    terrain: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    favorites: Mapped[list["Favorite"]] = relationship(
        "Favorite",
        back_populates="planet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Planet id={self.id} name={self.name}>"

    def serialize(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "diameter": self.diameter,
            "rotation_period": self.rotation_period,
            "orbital_period": self.orbital_period,
            "gravity": self.gravity,
            "population": self.population,
            "surface_water": self.surface_water,
            "climate": self.climate,
            "terrain": self.terrain,
        }


FavoriteType = Literal["person", "planet"]


class Favorite(db.Model):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    item_type: Mapped[str] = mapped_column(String(10), nullable=False)

    person_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), nullable=True
    )
    planet_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("planets.id", ondelete="CASCADE"), nullable=True
    )

    person: Mapped[Optional["Person"]] = relationship(
        "Person", back_populates="favorites")
    planet: Mapped[Optional["Planet"]] = relationship(
        "Planet", back_populates="favorites")

    user = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "( (person_id IS NOT NULL) <> (planet_id IS NOT NULL) )",
            name="ck_favorite_one_target",
        ),
        CheckConstraint(
            "(person_id IS NULL) OR (item_type = 'person')",
            name="ck_favorite_type_person",
        ),
        CheckConstraint(
            "(planet_id IS NULL) OR (item_type = 'planet')",
            name="ck_favorite_type_planet",
        ),
        UniqueConstraint("user_id", "person_id", "item_type",
                         name="uq_user_person_fav"),
        UniqueConstraint("user_id", "planet_id", "item_type",
                         name="uq_user_planet_fav"),
    )

    def __repr__(self) -> str:
        tgt = "person_id" if self.item_type == "person" else "planet_id"
        val = self.person_id if self.item_type == "person" else self.planet_id
        return f"<Favorite id={self.id} user_id={self.user_id} type={self.item_type} {tgt}={val}>"

    def serialize(self) -> dict:
        base = {"id": self.id, "user_id": self.user_id,
                "item_type": self.item_type}
        if self.item_type == "person" and self.person:
            base["person"] = self.person.serialize()
        if self.item_type == "planet" and self.planet:
            base["planet"] = self.planet.serialize()
        return base
