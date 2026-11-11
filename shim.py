#!/usr/bin/env python3
"""AgentGov Day 2, Step 2 - shim, minimal version 1.

The guard at the door. FastAPI, no UI.
An agent never writes directly. It asks this shim, and the shim
decides ALLOW or BLOCK, and only later versions will write the file.

What v1 does, on every call:
  1. Reads agents.yaml, humans.yaml, policies.oci fresh from this folder.
  2. Looks up the agent in agents.yaml - unknown agent = BLOCK.
  3. Suspended agent (status != active) = BLOCK.
  4. Parses policies.oci - Allow group X to read|manage RESOURCE
     in compartment Y - and checks the agent's group holds a
     matching line for that compartment and resource.
     Write needs manage. Read needs read or manage.
  5. No match = BLOCK. Fail closed.

What v1 does NOT do yet - next steps, one at a time:
  - No token check yet. No JWT, no token service.
  - No SoD / item-history check yet.
  - No fingerprint check yet.
  - No file write yet. It only answers ALLOW / BLOCK.
  - No audit log yet.

Run it (next step, not this one):
  python3 -m uvicorn shim:app --port 8000
Then, in another terminal:
  curl http://127.0.0.1:8000/health
"""
import re
from pathlib import Path

import yaml
from fastapi import FastAPI
from pydantic import BaseModel

BASE = Path(__file__).parent
COMPARTMENTS = ["Drafts", "Audit-Results", "Non-Production", "Production"]
# Compartment -> the resource type a policy line must name for it.
RESOURCE_FOR_COMPARTMENT = {
    "Drafts": "drafts",
    "Audit-Results": "audit-results",
    "Non-Production": "deployments",
    "Production": "deployments",
}
POLICY_RE = re.compile(
    r"^Allow group (\S+) to (read|manage) (\S+) in compartment (\S+)\s*$"
)

app = FastAPI(title="AgentGov shim")


class CheckRequest(BaseModel):
    agent_id: str
    action: str  # read or write
    compartment: str
    resource: str = ""


def load_registry():
    """Return (agents dict, policies list). Fail closed on any error."""
    agents_file = BASE / "agents.yaml"
    policies_file = BASE / "policies.oci"
    with open(agents_file, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    agents = {}
    for entry in data.get("agents", []):
        agents[str(entry.get("id"))] = entry
    policies = []
    with open(policies_file, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = POLICY_RE.match(line)
            if m:
                policies.append(
                    {
                        "group": m.group(1),
                        "verb": m.group(2),
                        "resource": m.group(3),
                        "compartment": m.group(4),
                    }
                )
    return agents, policies


def decide(agent_id, action, compartment, resource):
    """Return (allow, reason). Every unknown / mismatch is a BLOCK."""
    if action not in ("read", "write"):
        return False, "action must be read or write"
    if compartment not in COMPARTMENTS:
        return False, "unknown compartment: " + compartment
    want = resource or RESOURCE_FOR_COMPARTMENT[compartment]
    if want != RESOURCE_FOR_COMPARTMENT[compartment]:
        return False, "resource does not match compartment"
    try:
        agents, policies = load_registry()
    except Exception as e:
        return False, "cannot read registry/policies: " + str(e)
    agent = agents.get(agent_id)
    if agent is None:
        return False, "unknown agent: " + agent_id
    if str(agent.get("status")) != "active":
        return False, "agent is not active: " + agent_id
    group = str(agent.get("group"))
    for p in policies:
        if p["group"] != group:
            continue
        if p["compartment"] != compartment:
            continue
        if p["resource"] != want:
            continue
        if p["verb"] == "manage":
            return True, "ALLOW - group " + group + " can manage " + want
        if p["verb"] == "read" and action == "read":
            return True, "ALLOW - group " + group + " can read " + want
    return False, "BLOCK - group " + group + " holds no policy for this"


@app.get("/health")
def health():
    agents, policies = load_registry()
    return {"status": "ok", "agents": len(agents), "policies": len(policies)}


@app.post("/check")
def check(req: CheckRequest):
    allow, reason = decide(req.agent_id, req.action, req.compartment, req.resource)
    return {
        "agent_id": req.agent_id,
        "action": req.action,
        "compartment": req.compartment,
        "allow": allow,
        "decision": "ALLOW" if allow else "BLOCK",
        "reason": reason,
    }


@app.get("/matrix")
def matrix():
    agents, _policies = load_registry()
    out = {}
    for agent_id in sorted(agents):
        out[agent_id] = {}
        for comp in COMPARTMENTS:
            w, _ = decide(agent_id, "write", comp, "")
            r, _ = decide(agent_id, "read", comp, "")
            out[agent_id][comp] = {
                "write": "ALLOW" if w else "BLOCK",
                "read": "ALLOW" if r else "BLOCK",
            }
    return out
