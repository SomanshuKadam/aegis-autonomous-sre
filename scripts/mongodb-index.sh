#!/bin/sh
set -eu

MODE="${1:-}"

: "${MONGO_INITDB_ROOT_USERNAME:?MongoDB username is not configured}"
: "${MONGO_INITDB_ROOT_PASSWORD:?MongoDB password is not configured}"
: "${MONGO_INITDB_DATABASE:?MongoDB database is not configured}"

run_mongosh() {
  mongosh "$MONGO_INITDB_DATABASE" --quiet \
    --username "$MONGO_INITDB_ROOT_USERNAME" \
    --password "$MONGO_INITDB_ROOT_PASSWORD" \
    --authenticationDatabase admin \
    --eval "$1"
}

case "$MODE" in
  create)
    run_mongosh 'db.mycollection.createIndex({ searchField: 1 })'
    ;;
  verify)
    run_mongosh 'if (!db.mycollection.getIndexes().some(i => i.name === "searchField_1")) { quit(2) }'
    ;;
  list)
    run_mongosh 'db.mycollection.getIndexes().map(i => i.name)'
    ;;
  drop)
    run_mongosh 'if (db.mycollection.getIndexes().some(i => i.name === "searchField_1")) { db.mycollection.dropIndex("searchField_1") }'
    ;;
  *)
    printf 'usage: %s create|verify|list|drop\n' "$0" >&2
    exit 64
    ;;
esac
