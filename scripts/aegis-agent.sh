#!/bin/sh
set -eu

MODE="${1:-}"
TRACE_ID="${2:-}"
STATE_DIR=/opt/aegis/state
ANALYSIS_FILE="$STATE_DIR/${TRACE_ID}.analysis.json"

case "$TRACE_ID" in
  *[!0-9a-f]*|'')
    printf 'invalid trace_id\n' >&2
    exit 64
    ;;
esac

if [ "${#TRACE_ID}" -ne 32 ]; then
  printf 'invalid trace_id\n' >&2
  exit 64
fi

mkdir -p "$STATE_DIR"

case "$MODE" in
  analyze)
    PROMPT="You are the analysis stage of the Aegis local SRE pipeline. Use only the SigNoz MCP tools to inspect trace ${TRACE_ID}. Identify the slow MongoDB span and determine whether a missing ascending index on mydatabase.mycollection.searchField is the supported root cause. Do not run shell commands and do not mutate anything. Mark safe_to_remediate true only when that fresh trace explicitly shows db.system=mongodb, db.namespace=mydatabase, db.collection.name=mycollection, db.query.summary identifying searchField, and aegis.index_present=false on the relevant slow span. Return the required JSON only."
    timeout 240 codex --ask-for-approval never exec --skip-git-repo-check \
      --sandbox read-only \
      --output-schema /opt/aegis/analysis-output.schema.json \
      --output-last-message "$ANALYSIS_FILE" \
      "$PROMPT" </dev/null >/dev/null
    node -e 'const fs=require("fs"); const p=process.argv[1]; const t=process.argv[2]; const x=JSON.parse(fs.readFileSync(p,"utf8")); if(x.trace_id!==t || x.safe_to_remediate!==true || x.database!=="mydatabase" || x.collection!=="mycollection" || x.field!=="searchField" || x.recommended_command!=="docker exec mongodb sh /opt/aegis/mongodb-index.sh create") process.exit(1); process.stdout.write(JSON.stringify(x)+"\n")' "$ANALYSIS_FILE" "$TRACE_ID"
    ;;
  remediate)
    test -s "$ANALYSIS_FILE"
    node -e 'const fs=require("fs"); const x=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); if(x.trace_id!==process.argv[2] || x.safe_to_remediate!==true || x.database!=="mydatabase" || x.collection!=="mycollection" || x.field!=="searchField") process.exit(1)' "$ANALYSIS_FILE" "$TRACE_ID"
    REMEDIATION_FILE="$STATE_DIR/${TRACE_ID}.remediation.json"
    PROMPT="You are the bounded remediation stage of Aegis. Analysis in ${ANALYSIS_FILE} has authorized exactly one reversible local operation. Execute exactly this non-interactive command and no other mutation: docker exec mongodb sh /opt/aegis/mongodb-index.sh create. Then run exactly this read-only verification: docker exec mongodb sh /opt/aegis/mongodb-index.sh verify. Credentials are expanded only inside the controlled MongoDB container. Return the required JSON only with trace_id ${TRACE_ID}."
    timeout 240 codex --ask-for-approval never exec --skip-git-repo-check \
      --sandbox danger-full-access \
      --output-schema /opt/aegis/remediation-output.schema.json \
      --output-last-message "$REMEDIATION_FILE" \
      "$PROMPT" </dev/null >/dev/null
    node -e 'const fs=require("fs"); const x=JSON.parse(fs.readFileSync(process.argv[1],"utf8")); if(x.trace_id!==process.argv[2] || x.executed!==true || x.verified!==true || x.index_name!=="searchField_1") process.exit(1)' "$REMEDIATION_FILE" "$TRACE_ID"
    docker exec mongodb sh /opt/aegis/mongodb-index.sh verify
    node -e 'const fs=require("fs"); process.stdout.write(JSON.stringify(JSON.parse(fs.readFileSync(process.argv[1],"utf8")))+"\n")' "$REMEDIATION_FILE"
    ;;
  *)
    printf 'usage: %s analyze|remediate TRACE_ID\n' "$0" >&2
    exit 64
    ;;
esac
