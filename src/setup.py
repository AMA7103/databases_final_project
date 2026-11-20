import subprocess
from pathlib import Path

from db import test_connections


ROOT_DIR = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT_DIR / "schema"


def run_schema(filename, command):
    path = SCHEMA_DIR / filename

    print(f"Initializing {filename}...", flush=True)

    with path.open("r", encoding="utf-8") as file:
        subprocess.run(
            command,
            stdin=file,
            cwd=ROOT_DIR,
            check=True
        )

    print(f"Completed {filename}")


def initialize_mysql():
    run_schema(
        "mysql.sql",
        [
            "docker", "compose", "exec", "-T",
            "mysql", "mysql", "-u", "root"
        ]
    )


def initialize_mongodb():
    run_schema(
        "mongodb.js",
        [
            "docker", "compose", "exec", "-T",
            "mongodb", "sh", "-c",
            'mongosh --quiet '
            '-u "$MONGO_INITDB_ROOT_USERNAME" '
            '-p "$MONGO_INITDB_ROOT_PASSWORD" '
            '--authenticationDatabase admin '
            '--file /dev/stdin'
        ]
    )


def initialize_neo4j():
    run_schema(
        "neo4j.cypher",
        [
            "docker", "compose", "exec", "-T",
            "neo4j", "sh", "-c",
            'cypher-shell -u neo4j '
            '-p "${NEO4J_AUTH#*/}" -d neo4j'
        ]
    )


def initialize_databases():
    initialize_mysql()
    initialize_mongodb()
    initialize_neo4j()

    # Redis creates keys when data is inserted
    print("Redis: No schema initialization needed")

    test_connections()
    print("Database initialization complete.")


if __name__ == "__main__":
    initialize_databases()
