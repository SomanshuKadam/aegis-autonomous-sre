# Aegis action handler scope

Only the `action-runner` Compose service is assigned `AEGIS_MUTATION_CAPABILITY=runner`.
All API, workload, inventory, and worker services declare `none`; they may collect evidence,
record lifecycle state, or request actions, but cannot perform remediation.

The runner accepts only registered handlers:

- `mongo.create_search_index@1` creates the exact approved catalog index.
- `inventory.restore_capacity@1` restores a bounded inventory dependency capacity.
- `worker.set_capacity@1` adjusts an order worker pool inside configured bounds.

Each proposal must match a registered target and parameter shape, satisfy policy and any required
approval, pass the desired-state guard, and use the incident/evidence operation key exactly once.
