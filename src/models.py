from __future__ import annotations
from typing import Optional, Literal

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String, Boolean, ForeignKey, CheckConstraint, Enum, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "email": self.email,
            # do not serialize the password, its a security breach
        }


class Person(db.Model):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mass: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hair_color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    skin_color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    eye_color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def serialize(self):
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

# -----------------------
# Planet (updated types)
# -----------------------


class Planet(db.Model):
    __tablename__ = "planets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    diameter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rotation_period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    orbital_period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gravity: Mapped[str | None] = mapped_column(String(30), nullable=True)
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    surface_water: Mapped[int | None] = mapped_column(Integer, nullable=True)
    climate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    terrain: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def serialize(self):
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


# -----------------------
# Favorite (polymorphic to Person or Planet)
# -----------------------
FavoriteType = Literal["person", "planet"]


class Favorite(db.Model):
    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True)

    # who favorited it
    user_id: Mapped[int] = mapped_column(ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="favorites")

    # what type of thing is favorited
    item_type: Mapped[FavoriteType] = mapped_column(
        Enum("person", "planet", name="favorite_type"), nullable=False)

    # target (exactly one must be non-null, matching item_type)
    person_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), nullable=True)
    planet_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("planets.id", ondelete="CASCADE"), nullable=True)

    person: Mapped[Optional["Person"]] = relationship()
    planet: Mapped[Optional["Planet"]] = relationship()

    # ensure we don't save duplicates per user per item
    __table_args__ = (
        # only one of person_id / planet_id must be set
        CheckConstraint(
            "(person_id IS NOT NULL AND planet_id IS NULL) OR "
            "(person_id IS NULL AND planet_id IS NOT NULL)",
            name="ck_favorites_exactly_one_target",
        ),
        # item_type must match which FK is set
        CheckConstraint(
            "(item_type = 'person' AND person_id IS NOT NULL AND planet_id IS NULL) OR "
            "(item_type = 'planet' AND planet_id IS NOT NULL AND person_id IS NULL)",
            name="ck_favorites_type_matches_target",
        ),
        # prevent duplicates (user can't favorite the same item twice)
        UniqueConstraint("user_id", "item_type", "person_id",
                         name="uq_user_person_fav"),
        UniqueConstraint("user_id", "item_type", "planet_id",
                         name="uq_user_planet_fav"),
    )

    def serialize(self):
        base = {
            "id": self.id,
            "user_id": self.user_id,
            "item_type": self.item_type,
        }
        if self.item_type == "person" and self.person:
            base["person"] = self.person.serialize()
        if self.item_type == "planet" and self.planet:
            base["planet"] = self.planet.serialize()
        return base

    def __repr__(self) -> str:
        target = f"person_id={self.person_id}" if self.item_type == "person" else f"planet_id={self.planet_id}"
        return f"<Favorite id={self.id} user_id={self.user_id} type={self.item_type} {target}>"
