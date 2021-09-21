import json
from logging import currentframe
import os
from flask import Flask, jsonify
from flask_cors import CORS
import redis
from db import db
import mysql.connector
from mysql.connector import errorcode

app = Flask(__name__)
cors = CORS(app, resources={f"*": {"origins": "*"}})

redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = os.environ.get('REDIS_PORT', '6379')
red = redis.Redis(host=redis_host, port=redis_port)

local_db = os.environ.get('LOCAL_DB', 'false') in ['True', 'true']
db_host = os.environ.get('DB_HOST', 'localhost')
db_user = os.environ.get('DB_USER', 'root')
db_passwd = os.environ.get('DB_PASSWORD', 'myAwesomePassword')
db_name = os.environ.get('DATABASE', 'mydb')

mydb = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_passwd
    )
cursor = mydb.cursor()


def create_db(cursor):
    try:
        cursor.execute(
            "CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format(db_name))
    except mysql.connector.Error as err:
        print("Failed creating database: {}".format(err))
        exit(1)

try:
    cursor.execute("USE {}".format(db_name))
except mysql.connector.Error as err:
    print("Database {} does not exists.".format(db_name))
    if err.errno == errorcode.ER_BAD_DB_ERROR:
        create_db(cursor)
        print("Database {} created successfully.".format(db_name))
        mydb.database = db_name
    else:
        print(err)
        exit(1)

def create_table():
    try:
        print("Creating table users")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS `users`(
            `id` int NOT NULL,
            `title` varchar(50) NOT NULL,
            `createdBy` int NOT NULL,
            PRIMARY KEY (`id`)
            );
        """)
        
        cursor.execute("""
            insert into `users`(`id`,`title`,`createdBy`) 
                values (5,'users up and running!',2);
        """)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
            print("already exists.")
        else:
            print(err.msg)
    else:
        print("OK")

create_table()
    
def get_from_db(table):
    if local_db:
        return db.get(table)
    try:
        cursor.execute(f"SELECT * FROM {table}")
        return cursor.fetchall()
    except Exception as error:
        return "SQL error running: " + str(error)
 

@app.route('/api/users', methods=['GET'], strict_slashes=False)
def users():
    body = {}
    key = "users"
    try:
        value = red.get(key)
        if not value:
            users = get_from_db(key)
            red.set(key, str(json.dumps(users)))

            body['source'] = 'database'
            body['data'] = users
        else:
            body['source'] = 'redis'
            body['data'] = json.loads(value.decode('ascii'))

        print("Body:")
        print(body)
        return jsonify(body), 200
    except Exception as error: 
        print(error)
        body['data'] = error
        return str(error), 200

@app.route('/api/users/clear-cache', methods=['GET'], strict_slashes=False)
def clear_cache():
    red.delete("users")

    return "cleared users", 200


if __name__ == '__main__':
    app.run()