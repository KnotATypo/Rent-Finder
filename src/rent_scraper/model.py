import os
from pathlib import Path

from peewee import (
    Model,
    PostgresqlDatabase,
    TextField,
    IntegerField,
    AutoField,
    FloatField,
    ForeignKeyField,
    DateTimeField,
    BooleanField,
    CompositeKey,
    ProgrammingError,
)

db = PostgresqlDatabase(
    "rent-finder",
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    host=os.getenv("DB_HOST"),
)
db.connect()


class BaseModel(Model):
    class Meta:
        database = db


class Address(BaseModel):
    id = AutoField(primary_key=True)
    address = TextField()
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)
    updated = BooleanField()


class AddressHistory(BaseModel):
    address = ForeignKeyField(Address)
    beds = IntegerField()
    baths = IntegerField()
    cars = IntegerField()
    valid_from = DateTimeField()

    class Meta:
        primary_key = CompositeKey("address", "valid_from")


# Representation of view created by script
class SimpleAddress(BaseModel):
    id = TextField(primary_key=True)
    beds = IntegerField()
    baths = IntegerField()
    cars = IntegerField()

    class Meta:
        table_name = "simpleaddressview"

class Listing(BaseModel):
    id = TextField(primary_key=True)
    address = ForeignKeyField(Address)


class ListingHistory(BaseModel):
    listing = ForeignKeyField(Listing)
    price = IntegerField()
    valid_from = DateTimeField()
    valid_until = DateTimeField(null=True)

    class Meta:
        primary_key = CompositeKey("listing", "valid_from")


# Representation of view created by script
class SimpleListing(BaseModel):
    id = TextField(primary_key=True)
    address = ForeignKeyField(SimpleAddress)
    price = IntegerField()
    available = BooleanField()

    class Meta:
        table_name = "simplelistingview"


class Query(BaseModel):
    lower_price = IntegerField(null=True)
    upper_price = IntegerField(null=True)
    beds = TextField(null=True)


class GeocodeFails(BaseModel):
    address = TextField()


db.create_tables([Address, Listing, GeocodeFails, ListingHistory, AddressHistory], safe=True)

# Try to read from the address view to check if the db setup has run
try:
    SimpleAddress.select().get()
except ProgrammingError:
    setup_file = Path(__file__).parent / "resources" / "first_time_setup.sql"
    cursor = db.cursor()
    with open(setup_file) as f:
        command = f.read()
    cursor.execute(command)
