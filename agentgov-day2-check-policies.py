#!/usr/bin/env python3
"""AgentGov Day 2, Step 1 — deterministic policy checker (no LLM, no UI).

Reads the three files that already exist in this folder and answers, in
plain words, whether what they say matches what was designed:

  agents.yaml   — who the agents are, and which group each one is in
  humans.yaml   — which roles Shivoy holds, and which group each role is in
  policies.oci  — what each group can do, in which compartment (group-only)

It checks:
  C1  every group named in policies.oci exists in agents.yaml/humans.yaml
  C2  every compartment named in policies.oci is one of the 4 real ones
  C3  every policy line matches OCI syntax:
      Allow group <group> to <read|manage> <resource> in compartment <name>
  C4  no duplicate policy line
  C5  every agent group holds at least one policy
  C6  no agent can write to Production (only the human prod-deployers
      group holds that; an agent group holding it would break SoD)
  C7  the 3 governance-only groups (approvers, platform-admins,
      break-glass) hold NO compartment policy — by design, reported
      as INFO, not a failure

Then it prints an allow/block matrix: for each agent, for each
compartment, can it read? can it write? That is the live proof the YAML
is not just paper — the same answers the shim will enforce on Day 2.

Usage (one step, from inside the AgentGov repo folder on your Mac):
  python3 check_policies.py
  — or, from anywhere:  python3 check_policies.py /path/to/AgentGov-folder

Exit code 0 = all checks pass. Exit code 1 = something failed; the
failing check names the exact line or group, so you fix that one thing.

This file reads only. It changes nothing, writes nothing, and never
touches the network. Requires Python 3 + PyYAML (macOS: python3 -m pip
install pyyaml — only if the import fails).
"""

import re
import sys
from pathlib import Path

COMPARTMENTS = ["Drafts", "Audit-Results", "Non-Production", "Production"]
# The three resource types this PoC uses. In real OCI these would map to
# real resource types; here they are the PoC's own words. Anything else —
# e.g. "manage Production" — repeats the mistake Shivoy caught on Nov 7:
# you manage a resource IN a compartment, never the compartment itself.
RESOURCES = {"drafts", "audit-results", "deployments"}
# Groups that are meant to hold NO compartment policy. Their access lives
# in humans.yaml as a capability (REGISTRY_ADMIN / EMERGENCY_PLATFORM),
# not as a policies.oci line. See the crisp runbook, pages 4-5.
GOVERNANCE_ONLY_GROUPS = {"approvers", "platform-admins", "break-glass"}
POLICY_RE = re.compile(
    r"^Allow group (\S+) to (read|manage) (\S+) in compartment (\S+)\s*$"
)


def load_yaml(path):
    """Load a YAML file. Falls back to a tiny hand parser if PyYAML is
    missing, so the check still runs — it only needs id/role/name + group."""
    try:
        import yaml
    except ImportError:
        yaml = None
    if yaml is not None:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    # Fallback: collect (label, group) pairs line by line.
    pairs = []
    label = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*-\s*(?:id|role|name):\s*(\S+)", line)
            if m:
                label = m.group(1)
            g = re.match(r"\s*group:\s*(\S+)", line)
            if g:
                pairs.append((label or "?", g.group(1)))
    return {"_fallback_pairs": pairs}


def collect_group_members(data):
    """Walk parsed YAML and return [(label, group)] for every dict that
    carries a 'group' key. Label comes from a sibling id / role / name."""
    found = []
    if isinstance(data, dict) and "_fallback_pairs" in data:
        return data["_fallback_pairs"]

    def walk(node):
        if isinstance(node, dict):
            if "group" in node:
                label = node.get("id") or node.get("role") or node.get("name") or "?"
                found.append((str(label), str(node["group"])))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return found


def parse_policies(path):
    """Return (policies, bad_lines). A policy is (group, verb, resource,
    compartment, line_no)."""
    policies, bad = [], []
    with open(path, encoding="utf-8") as f:
        for no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = POLICY_RE.match(line)
            if m:
                policies.append((m.group(1), m.group(2), m.group(3), m.group(4), no))
            else:
                bad.append((no, line))
    return policies, bad


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent
    agents_file = folder / "agents.yaml"
    humans_file = folder / "humans.yaml"
    policies_file = folder / "policies.oci"
    failures, notes = [], []

    for p in (agents_file, humans_file, policies_file):
        if not p.exists():
            print(f"FAIL  missing file: {p.name} (expected in {folder})")
            return 1

    agent_members = collect_group_members(load_yaml(agents_file))
    human_members = collect_group_members(load_yaml(humans_file))
    agents = {label: group for label, group in agent_members}
    registry_groups = {group for _, group in agent_members + human_members}
    policies, bad_lines = parse_policies(policies_file)

    print(f"Registry: {len(agents)} agent(s), "
          f"{len(human_members)} human role(s), "
          f"{len(registry_groups)} group(s), {len(policies)} polic(ies).")

    # C3 — syntax first, so later checks read real policies only.
    for no, line in bad_lines:
        failures.append(f"C3  line {no} is not valid policy syntax: {line}")
    for group, verb, resource, compartment, no in policies:
        if resource.lower() not in RESOURCES:
            failures.append(f"C3  line {no}: resource '{resource}' is not one of "
                            f"{sorted(RESOURCES)} — you manage a resource in a "
                            f"compartment, never the compartment itself")
    # C4 — duplicates.
    seen = {}
    for group, verb, resource, compartment, no in policies:
        key = (group, verb, resource, compartment)
        if key in seen:
            failures.append(f"C4  duplicate policy, lines {seen[key]} and {no}: "
                            f"Allow group {group} to {verb} {resource} "
                            f"in compartment {compartment}")
        seen[key] = no
    # C1 — policy groups must exist in the registry.
    for group, verb, resource, compartment, no in policies:
        if group not in registry_groups:
            failures.append(f"C1  line {no}: group '{group}' is in policies.oci "
                            f"but in no registry file (agents.yaml / humans.yaml) — drift")
    # C2 — compartments must be one of the 4.
    for group, verb, resource, compartment, no in policies:
        if compartment not in COMPARTMENTS:
            failures.append(f"C2  line {no}: compartment '{compartment}' is not "
                            f"one of {COMPARTMENTS}")
    # C5 — every agent group must hold at least one policy.
    policy_groups = {group for group, *_ in policies}
    for label, group in sorted(agents.items()):
        if group not in policy_groups:
            failures.append(f"C5  agent '{label}' is in group '{group}', "
                            f"but that group holds no policy")
    # C6 — no agent may write to Production.
    for group, verb, resource, compartment, no in policies:
        if compartment == "Production" and verb == "manage":
            holders = [a for a, g in agents.items() if g == group]
            if holders:
                failures.append(f"C6  line {no}: agent group '{group}' can manage "
                                f"in Production (agent(s): {', '.join(holders)}) — SoD break")
    # C7 — governance-only groups hold no compartment policy (by design).
    for group in sorted(GOVERNANCE_ONLY_GROUPS & policy_groups):
        notes.append(f"INFO C7  group '{group}' holds a compartment policy — "
                     f"expected NONE (its access is a humans.yaml capability)")

    # Allow / block matrix: read = read or manage; write = manage only.
    def allowed(group, compartment, want_write):
        for g, verb, _res, comp, _no in policies:
            if g == group and comp == compartment:
                if verb == "manage":
                    return True
                if verb == "read" and not want_write:
                    return True
        return False

    print()
    print("Allow / block — write access (manage):")
    header = "agent".ljust(24) + "".join(c.ljust(16) for c in COMPARTMENTS)
    print(header)
    for label in sorted(agents):
        row = label.ljust(24)
        for comp in COMPARTMENTS:
            row += ("ALLOW" if allowed(agents[label], comp, True) else "BLOCK").ljust(16)
        print(row)
    print()
    print("Allow / block — read access:")
    print(header)
    for label in sorted(agents):
        row = label.ljust(24)
        for comp in COMPARTMENTS:
            row += ("ALLOW" if allowed(agents[label], comp, False) else "BLOCK").ljust(16)
        print(row)

    print()
    for note in notes:
        print(note)
    if failures:
        print(f"FAIL  {len(failures)} check(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"PASS  all checks passed — {len(policies)} policies, "
          f"{len(agents)} agents, groups match the registry, "
          f"no agent can write Production.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
