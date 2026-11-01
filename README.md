# AgentGov - Agent Identity Governance Platform

## Problem
AI agents that draft infrastructure code should not also check and ship their own work. If one agent can draft and deploy, one hallucination or injected instruction can go to production unchecked, with no proof of who did what.

AgentGov treats AI agents as first-class identities: each agent has an owner, a group, a status, and only the access its compartment allows. The agent that makes a change is never the agent that checks it, and never the agent that ships it.

## Day 1 - Built so far
- Agent registry: `agents.yaml`
  - infra-drafter: Drafts only, DRAFT_WRITE
  - security-auditor: reads Drafts, writes Audit-Results only, AUDIT_WRITE
  - No admin agent. No deployer yet.
- Policies: `policies.oci`, in real OCI IAM policy syntax
  - infra-drafters manage drafts in Drafts
  - security-auditors read drafts in Drafts
  - security-auditors manage audit-results in Audit-Results
  - Anything not listed is denied by default.
- Compartments: Drafts, Audit-Results. Production is planned, simulated, not built yet.
- Owner: Shivoy Malhotra. Kill switch: change an agent's status in `agents.yaml` from active to suspended, and its next call is blocked.

## Day 1 proof - ITEM-001
- Draft: `Drafts/item-001.tf` - private VCN, private subnet, no public IP
- Drafted by: infra-drafter
- Audit: `Audit-Results/item-001.yaml`
- Audited by: security-auditor
- Verdict: PASS, Impact: LOW, Status: AUDIT_PASSED

## Honest limits - Not built yet
- No infra-deployer, no human gate, no post-deploy verification yet. Those start only after this draft-to-audit path works.
- No FastAPI shim, no local token service, no Entra ID login, no SQLite stores, no Docker Compose yet. Those are planned, not claimed.
- No real OCI tenancy, no real infrastructure created or changed. Production, when built, will be simulated locally.
- The reference PDF in the local folder is not part of this repo and is not pushed to GitHub.

## Next steps
1. Add infra-deployer, human gate for HIGH impact, and post-deploy verification.
2. Build the enforcement shim, token service, and policy parser that check registry, policy, and item history on every call.
