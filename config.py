from pymongo import MongoClient

WTF_CSRF_ENABLED = True
SECRET_KEY = 'not-so-secret'

DB_NAME = 'cgviz'
DATABASE = MongoClient()[DB_NAME]
SAMPLES_COLL = DATABASE.sample
SPECIES_COLL = DATABASE.species
SCHEMES_COLL = DATABASE.scheme

USER_DB_NAME = 'coyote'
USER_DATABASE = MongoClient()[USER_DB_NAME]
USERS_COLL = USER_DATABASE.users

DEBUG = True
