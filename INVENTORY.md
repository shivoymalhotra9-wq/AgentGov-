# AgentGov - Agent Inventory
## One governed view - SailPoint-like, vendor-neutral

| Agent | Owner | Group | Status | Access | Last audit | Access review |
|---|---|---|---|---|---|---|
| infra-drafter | Shivoy Malhotra | infra-drafters | active | DRAFT_WRITE, Drafts only | ITEM-001, drafted, AUDIT_PASSED | Not yet certified |
| security-auditor | Shivoy Malhotra | security-auditors | active | AUDIT_WRITE, Audit-Results only; read Drafts | ITEM-001, PASS, LOW, AUDIT_PASSED | Not yet certified |

## Ownership check
- Both agents have a human owner: Shivoy Malhotra.
- No orphan agents: no agent in the registry without an owner.
- Succession: if the owner changes, ownership must be reassigned in agents.yaml before the next audit cycle, so governance never falls through the cracks.

## Shadow check - Day 1
- Agents found in Drafts and Audit-Results: infra-drafter, security-auditor only.
- Unknown agents: none found. No agent acted that is not in the registry.
- This is a manual Day 1 check. Automated discovery is a later stage, not claimed here.

## Notes
- No admin agent. No deployer yet.
- Production access: none, until the deployer stage.
- This inventory is built from agents.yaml, policies.oci, and Audit-Results/item-001.yaml. If those files change, this inventory must be updated in the same change.
