import os
from pathlib import Path

import mysql.connector
from pymongo import MongoClient
import redis
from neo4j import GraphDatabase
from dotenv import load_dotenv


# Load environment variables from the project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


# MySQL connection
def get_mysql_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        database=os.getenv("MYSQL_DATABASE"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        connection_timeout=5,
    )


# MongoDB connection
def get_mongo_client():
    return MongoClient(
        host=os.getenv("MONGO_HOST"),
        port=int(os.getenv("MONGO_PORT", 27017)),
        username=os.getenv("MONGO_INITDB_ROOT_USERNAME"),
        password=os.getenv("MONGO_INITDB_ROOT_PASSWORD"),
        authSource="admin",
        serverSelectionTimeoutMS=5000,
    )


# Redis connection
def get_redis_client():
    return redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


# Neo4j connection
def get_neo4j_driver():
    uri = (
        f"bolt://{os.getenv('NEO4J_HOST')}:"
        f"{os.getenv('NEO4J_BOLT_PORT', 7687)}"
    )

    return GraphDatabase.driver(
        uri,
        auth=(
            os.getenv("NEO4J_USER"),
            os.getenv("NEO4J_PASSWORD"),
        ),
        connection_timeout=5,
    )


# Verify all four connections
def test_connections():

    # MySQL
    connection = get_mysql_connection()
    try:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT 1")
            cursor.fetchone()
            print("MySQL: Connected")
        finally:
            cursor.close()
    finally:
        connection.close()

    # MongoDB
    client = get_mongo_client()
    try:
        client.admin.command("ping")
        print("MongoDB: Connected")
    finally:
        client.close()

    # Redis
    client = get_redis_client()
    try:
        client.ping()
        print("Redis: Connected")
    finally:
        client.close()

    # Neo4j
    driver = get_neo4j_driver()
    try:
        database = os.getenv("NEO4J_DATABASE", "neo4j")
        with driver.session(database=database) as session:
            session.run("RETURN 1").consume()
        print("Neo4j: Connected")
    finally:
        driver.close()


if __name__ == "__main__":
    test_connections()
