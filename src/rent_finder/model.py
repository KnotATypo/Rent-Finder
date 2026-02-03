import os
from dataclasses import dataclass
from enum import Enum

from peewee import Model, PostgresqlDatabase, TextField, IntegerField, AutoField, FloatField, ForeignKeyField
from peewee_enum_field import EnumField

db = PostgresqlDatabase(
    "rent-finder",
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    host=os.getenv("DB_HOST"),
)
db.connect()


class Status(Enum):
    NEW = "New"
    INTERESTED = "Interested"
    NOT_INTERESTED = "Not Interested"
    OFF_MARKET = "Off-Market"


class TravelMode(Enum):
    PT = "PT"
    BIKE = "Bike"
    CAR = "Car"


@dataclass
class Coordinate:
    lat: float
    lon: float

    def __str__(self):
        return f"({self.lat}, {self.lon})"


class Address(Model):
    id = AutoField(primary_key=True)
    address = TextField()
    beds = IntegerField()
    baths = IntegerField()
    cars = IntegerField()
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)

    class Meta:
        database = db


class Listing(Model):
    id = TextField(primary_key=True)
    address_id = ForeignKeyField(Address)
    price = IntegerField()

    class Meta:
        database = db


class SavedLocations(Model):
    id = AutoField(primary_key=True)
    latitude = FloatField()
    longitude = FloatField()
    name = TextField()

    class Meta:
        database = db


class TravelTime(Model):
    id = AutoField(primary_key=True)
    address_id = ForeignKeyField(Address)
    travel_time = IntegerField()
    travel_mode = EnumField(TravelMode)
    to_location = ForeignKeyField(SavedLocations)

    class Meta:
        database = db


class User(Model):
    id = AutoField(primary_key=True)
    username = TextField()

    class Meta:
        database = db


class AddressStatus(Model):
    id = AutoField(primary_key=True)
    address_id = ForeignKeyField(Address)
    user_id = ForeignKeyField(User)
    status = EnumField(Status, default=Status.NEW)

    class Meta:
        database = db


class Suburb(Model):
    id = AutoField(primary_key=True)
    name = TextField()
    postcode = IntegerField()
    latitude = FloatField()
    longitude = FloatField()
    distance_to_source = FloatField()  # Centre point of search

    class Meta:
        database = db


db.create_tables([Address, Listing, TravelTime, SavedLocations, User, AddressStatus, Suburb], safe=True)
