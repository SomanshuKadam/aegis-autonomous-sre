# Aegis Logical Agent Schemas

Versioned JSON schemas in this directory define the accepted structured inputs and outputs for
Aegis logical agent roles. Each schema name uses the `<role>-output.schema.json` convention and
includes a `schema` field with a stable `aegis.agent.<role>.v<major>` value.

Schemas validate data only. They never authorize a mutation, define an executable command, or
contain credentials. The existing baseline schemas at `codex/` remain in place until their callers
are migrated.
