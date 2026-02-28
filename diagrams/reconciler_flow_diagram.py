#!/usr/bin/env python3
"""Reconciler Decision Flow diagram — step-by-step logic with classification engine."""

import os
import graphviz

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT = "Helvetica Neue,Helvetica,Arial"

# Colors
TRIGGER = "#a29bfe"
STEP = "#74b9ff"
DECISION = "#ffeaa7"
ENGINE = "#fd79a8"
CLASSIFY = "#dfe6e9"
NOACT = "#b2bec3"
DISPATCH = "#55efc4"
SUCCESS = "#00b894"
FAIL = "#ff7675"
ALERT = "#d63031"
SKIP = "#636e72"


def node(g, nid, label, category="step"):
    """Helper to add styled nodes by category."""
    styles = {
        "trigger":  dict(shape="box", style="filled,rounded", fillcolor=TRIGGER, fontcolor="#ffffff", penwidth="2"),
        "step":     dict(shape="box", style="filled,rounded", fillcolor=STEP, fontcolor="#ffffff", penwidth="2"),
        "decision": dict(shape="diamond", style="filled", fillcolor=DECISION, fontcolor="#2d3436", penwidth="2"),
        "engine":   dict(shape="box", style="filled,rounded,bold", fillcolor=ENGINE, fontcolor="#ffffff", penwidth="2"),
        "classify": dict(shape="box", style="filled,rounded", fillcolor=CLASSIFY, fontcolor="#2d3436", penwidth="1"),
        "noact":    dict(shape="box", style="filled,rounded", fillcolor=NOACT, fontcolor="#2d3436", penwidth="1"),
        "dispatch": dict(shape="box", style="filled,rounded", fillcolor=DISPATCH, fontcolor="#2d3436", penwidth="2"),
        "success":  dict(shape="box", style="filled,rounded", fillcolor=SUCCESS, fontcolor="#ffffff", penwidth="2"),
        "fail":     dict(shape="box", style="filled,rounded", fillcolor=FAIL, fontcolor="#ffffff", penwidth="2"),
        "alert":    dict(shape="box", style="filled,rounded", fillcolor=ALERT, fontcolor="#ffffff", penwidth="2"),
        "skip":     dict(shape="box", style="filled,rounded", fillcolor=SKIP, fontcolor="#ffffff", penwidth="1"),
    }
    g.node(nid, label, **styles[category])


def create_reconciler_flow():
    g = graphviz.Digraph("reconciler_flow", format="png")
    g.attr(
        rankdir="TB",
        bgcolor="#ffffff",
        fontname=FONT,
        fontsize="20",
        label="Reconciler Decision Flow",
        labelloc="t",
        labeljust="c",
        pad="0.6",
        nodesep="0.5",
        ranksep="0.6",
        dpi="150",
    )
    g.attr("node", fontname=FONT, fontsize="10")
    g.attr("edge", fontname=FONT, fontsize="8")

    # ── Nodes ──────────────────────────────────────────

    node(g, "START", "Scheduler triggers\nReconciler run", "trigger")
    node(g, "QUERY", "Step 1: Query State Table\nfor stale, non-terminal PRs", "step")
    node(g, "CB_CHECK", "Circuit Breaker\nstatus?", "decision")
    node(g, "CB_OPEN", "Remediation paused\nSkip all PRs", "skip")
    node(g, "CB_HALF", "Cooldown\nelapsed?", "decision")
    node(g, "CB_PROBE", "Allow 1 PR\nas probe", "step")
    node(g, "POLL", "Step 3a: Poll GitHub API\n(trust but verify)", "step")
    node(g, "DRIFT", "State drift\ndetected?", "decision")
    node(g, "DRIFT_FIX", "Update State Table\nLog: STATE_DRIFT_CORRECTED", "step")
    node(g, "STILL_STALE", "Still stale after\ncorrection?", "decision")
    node(g, "CLASSIFY", "Classification Engine\n(priority order)", "engine")

    # Classification chain
    node(g, "C1", "1. Merge conflict?\n→ CLOSE_AND_REOPEN", "classify")
    node(g, "C2", "2. Branch behind?\n→ UPDATE_BRANCH", "classify")
    node(g, "C3", "3. Checks failed (transient)?\n→ RETRY_CHECKS", "classify")
    node(g, "C4", "4. Checks failed (persistent)?\n→ NEEDS_INTERVENTION", "classify")
    node(g, "C5", "5. Policy Bot stale?\n→ RETRIGGER_POLICY", "classify")
    node(g, "C6", "6. SOD failure?\n(Policy Bot or Approver Bot)\n→ RETRIGGER_SOD", "classify")
    node(g, "C7", "7. Permanent policy failure?\n(foreign commit · invalid file)\n→ CLOSE_PR", "classify")
    node(g, "C8", "8. Approver Bot stale?\n→ RETRIGGER_APPROVER", "classify")
    node(g, "C9", "9. Automerge stale?\n→ RETRIGGER_MERGE", "classify")
    node(g, "C10", "10. Within threshold?\n→ NO_ACTION", "noact")
    node(g, "C11", "11. Fallthrough\n→ NEEDS_INTERVENTION", "classify")

    node(g, "BUDGET", "Retry budget\nexhausted?", "decision")
    node(g, "ESCALATE", "→ NEEDS_INTERVENTION\nSend escalation notification", "alert")
    node(g, "DISPATCH", "Execute remediation\nEmit command to queue\nIncrement retry count", "dispatch")
    node(g, "OUTCOME", "Remediation\nsucceeded?", "decision")
    node(g, "SUCCESS", "Update State Table\nLog success", "success")
    node(g, "FAILURE", "Log failure details\nIncrement CB failure counter", "fail")
    node(g, "CB_UPDATE", "Failure rate >\nthreshold?", "decision")
    node(g, "CB_TRIP", "Trip circuit breaker → OPEN\nSend notification", "alert")
    node(g, "NEXT", "Next stale PR\n(or end run)", "step")

    # ── Edges: Main Flow ───────────────────────────────

    edge_default = dict(color="#2d3436", penwidth="1.5")
    edge_yes = dict(color="#00b894", fontcolor="#00b894", penwidth="1.5")
    edge_no = dict(color="#d63031", fontcolor="#d63031", penwidth="1.5")
    edge_label = dict(color="#2d3436", penwidth="1.5")

    g.edge("START", "QUERY", **edge_default)
    g.edge("QUERY", "CB_CHECK", **edge_default)

    g.edge("CB_CHECK", "CB_OPEN", label="OPEN", **edge_no)
    g.edge("CB_OPEN", "CB_HALF", **edge_default)
    g.edge("CB_HALF", "NEXT", label="No", **edge_no)
    g.edge("CB_HALF", "CB_PROBE", label="Yes (half-open)", **edge_yes)
    g.edge("CB_PROBE", "POLL", **edge_default)
    g.edge("CB_CHECK", "POLL", label="CLOSED", **edge_yes)

    g.edge("POLL", "DRIFT", **edge_default)
    g.edge("DRIFT", "DRIFT_FIX", label="Yes", **edge_yes)
    g.edge("DRIFT_FIX", "STILL_STALE", **edge_default)
    g.edge("STILL_STALE", "NEXT", label="No — skip", **edge_no)
    g.edge("STILL_STALE", "CLASSIFY", label="Yes", **edge_yes)
    g.edge("DRIFT", "CLASSIFY", label="No", **edge_label)

    # ── Edges: Classification Chain ────────────────────

    chain_no = dict(color="#636e72", fontcolor="#636e72", penwidth="1.0")
    chain_yes = dict(color="#00b894", fontcolor="#00b894", penwidth="1.5")

    g.edge("CLASSIFY", "C1", **edge_default)
    g.edge("C1", "C2", label="no", **chain_no)
    g.edge("C2", "C3", label="no", **chain_no)
    g.edge("C3", "C4", label="no", **chain_no)
    g.edge("C4", "C5", label="no", **chain_no)
    g.edge("C5", "C6", label="no", **chain_no)
    g.edge("C6", "C7", label="no", **chain_no)
    g.edge("C7", "C8", label="no", **chain_no)
    g.edge("C8", "C9", label="no", **chain_no)
    g.edge("C9", "C10", label="no", **chain_no)
    g.edge("C10", "C11", label="no", **chain_no)

    # "yes" branches → budget or escalation
    for c in ["C1", "C2", "C3", "C5", "C6", "C7", "C8", "C9"]:
        g.edge(c, "BUDGET", label="yes", **chain_yes)

    g.edge("C4", "ESCALATE", label="yes", color="#d63031", fontcolor="#d63031", penwidth="1.5")
    g.edge("C11", "ESCALATE", label="matched", color="#d63031", fontcolor="#d63031", penwidth="1.5")
    g.edge("C10", "NEXT", label="yes", color="#636e72", fontcolor="#636e72", penwidth="1.0")

    # ── Edges: Budget & Dispatch ───────────────────────

    g.edge("BUDGET", "ESCALATE", label="Exhausted", **edge_no)
    g.edge("BUDGET", "DISPATCH", label="OK", **edge_yes)
    g.edge("ESCALATE", "NEXT", **edge_default)

    g.edge("DISPATCH", "OUTCOME", **edge_default)
    g.edge("OUTCOME", "SUCCESS", label="Yes", **edge_yes)
    g.edge("OUTCOME", "FAILURE", label="No", **edge_no)

    g.edge("SUCCESS", "CB_UPDATE", **edge_default)
    g.edge("FAILURE", "CB_UPDATE", **edge_default)

    g.edge("CB_UPDATE", "CB_TRIP", label="Yes", **edge_no)
    g.edge("CB_UPDATE", "NEXT", label="No", **edge_yes)
    g.edge("CB_TRIP", "NEXT", **edge_default)

    return g


def main():
    g = create_reconciler_flow()
    for fmt in ["png", "svg"]:
        g.format = fmt
        g.render(filename=os.path.join(OUTPUT_DIR, "reconciler_flow"), cleanup=True)


if __name__ == "__main__":
    main()
