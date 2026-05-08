import os

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
    beds = IntegerField()
    baths = IntegerField()
    cars = IntegerField()
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)
    updated = BooleanField()


class Listing(BaseModel):
    id = TextField(primary_key=True)
    address = ForeignKeyField(Address)
    price = IntegerField()
    available = DateTimeField()
    unavailable = DateTimeField(null=True)


class Query(BaseModel):
    lower_price = IntegerField(null=True)
    upper_price = IntegerField(null=True)
    beds = TextField(null=True)


class GeocodeFails(BaseModel):
    address = TextField()


db.create_tables([Address, Listing, GeocodeFails], safe=True)
