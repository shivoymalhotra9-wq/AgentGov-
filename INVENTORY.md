# AgentGov - Agent Inventory
## One governed view - SailPoint-like, vendor-neutral

| Agent | Owner | Group | Status | Access | Last audit | Access review |
|---|---|---|---|---|---|---|
| infra-drafter | Shivoy Malhotra | infra-drafters | active | DRAFT_WRITE, Drafts only | ITEM-001, drafted, AUDIT_PASSED | Not yet certified |
| security-auditor | Shivoy Malhotra | security-auditors | active | AUDIT_WRITE, Audit-Results only; read Drafts | ITEM-001, PASS, LOW, AUDIT_PASSED | Not yet certified |
| infra-deployer-nonprod | Shivoy Malhotra | infra-deployers-nonprod | active | DEPLOY_WRITE, Non-Production only; read Drafts | ITEM-001, not yet deployed | Not yet certified |

## Ownership check
- All three agents have a human owner: Shivoy Malhotra.
- No orphan agents: no agent in the registry without an owner.
- Succession: if the owner changes, ownership must be reassigned in agents.yaml before the next audit cycle, so governance never falls through the cracks.

## Shadow check - Day 1
- Agents found in Drafts, Audit-Results, Non-Production, and Production: infra-drafter, security-auditor, infra-deployer-nonprod only.
- Unknown agents: none found. No agent acted that is not in the registry.
- This is a manual Day 1 check. Automated discovery is a later stage, not claimed here.

## Notes
- No admin agent. Deployer added, Non-Production only.
- Production access: human prod-deployer only, Shivoy Malhotra in humans.yaml. No agent can deploy to Production.
- This inventory is built from agents.yaml, policies.oci, humans.yaml, and Audit-Results/item-001.yaml. If those files change, this inventory must be updated in the same change.
