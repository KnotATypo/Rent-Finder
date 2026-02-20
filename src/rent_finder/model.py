import datetime
import operator
import os
from dataclasses import dataclass
from enum import Enum

from peewee import (
    Model,
    PostgresqlDatabase,
    TextField,
    IntegerField,
    AutoField,
    FloatField,
    ForeignKeyField,
    DateTimeField,
)
from peewee_enum_field import EnumField

db = PostgresqlDatabase(
    "rent-finder",
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    host=os.getenv("DB_HOST"),
)
db.connect()


class UserStatus(Enum):
    INTERESTED = "Interested"
    NOT_INTERESTED = "Not Interested"


class TravelMode(Enum):
    PT = "PT"
    BIKE = "Bike"
    CAR = "Car"


class FilterType(Enum):
    PRICE = "Price"
    BEDS = "Beds"

    def function(self):
        if self == FilterType.PRICE:
            return lambda l: l.price
        elif self == FilterType.BEDS:
            return lambda l: Address.select().join(Listing).where(Listing.id == l.id).get().beds


class Operator(Enum):
    LESS_EQ = "LessEq"
    GREATER_EQ = "GreaterEq"

    def function(self):
        if self == Operator.LESS_EQ:
            return operator.le
        elif self == Operator.GREATER_EQ:
            return operator.ge

    def display(self):
        if self == Operator.LESS_EQ:
            return "<="
        elif self == Operator.GREATER_EQ:
            return ">="


@dataclass
class Coordinate:
    lat: float
    lon: float

    def __str__(self):
        return f"({self.lat}, {self.lon})"


class BaseModel(Model):
    class Meta:
        database = db


class Address(BaseModel):
    id = AutoField(primary_key=True)
    address = TextField()
    beds = IntegerField()
    baths = IntegerField()
    cars = IntegerField()
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)


class Listing(BaseModel):
    id = TextField(primary_key=True)
    address = ForeignKeyField(Address)
    price = IntegerField()
    available = DateTimeField()
    unavailable = DateTimeField(null=True)


class SavedLocations(BaseModel):
    id = AutoField(primary_key=True)
    latitude = FloatField()
    longitude = FloatField()
    name = TextField()


class TravelTime(BaseModel):
    id = AutoField(primary_key=True)
    address = ForeignKeyField(Address)
    travel_time = IntegerField()
    travel_mode = EnumField(TravelMode)
    to_location = ForeignKeyField(SavedLocations)


class User(BaseModel):
    id = AutoField(primary_key=True)
    username = TextField()


class AddressStatus(BaseModel):
    id = AutoField(primary_key=True)
    address = ForeignKeyField(Address)
    user = ForeignKeyField(User)
    status = EnumField(UserStatus, null=True)


class Suburb(BaseModel):
    id = AutoField(primary_key=True)
    name = TextField()
    postcode = IntegerField()
    latitude = FloatField()
    longitude = FloatField()
    distance_to_source = FloatField()  # Centre point of search


class Filter(BaseModel):
    id = AutoField(primary_key=True)
    user = ForeignKeyField(User)
    type = EnumField(FilterType)
    operator = EnumField(Operator)
    value = IntegerField()


db.create_tables([Address, Listing, TravelTime, SavedLocations, User, AddressStatus, Suburb, Filter], safe=True)
