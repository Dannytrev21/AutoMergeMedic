#!/usr/bin/env python3
"""Sequence-style diagrams for AutoMergeMedic end-to-end flows.

Uses graphviz with ranked subgraphs to approximate swim-lane sequence diagrams.
Generates 3 separate diagrams: happy path, self-healing, command queue.
"""

import os
import graphviz

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT = "Helvetica Neue,Helvetica,Arial"

# Participant header colors
COLORS = {
    "codegenie":   ("#a29bfe", "#ffffff"),
    "github":      ("#2d3436", "#ffffff"),
    "car_bridge":  ("#6c5ce7", "#ffffff"),
    "event_proc":  ("#00b894", "#ffffff"),
    "datastore":   ("#fdcb6e", "#2d3436"),
    "policy_bot":  ("#0984e3", "#ffffff"),
    "approver_bot":("#0984e3", "#ffffff"),
    "automerge":   ("#0984e3", "#ffffff"),
    "scheduler":   ("#d63031", "#ffffff"),
    "reconciler":  ("#d63031", "#ffffff"),
    "github_api":  ("#2d3436", "#ffffff"),
    "classifier":  ("#e84393", "#ffffff"),
    "cmd_queue":   ("#6c5ce7", "#ffffff"),
    "jenkins":     ("#636e72", "#ffffff"),
    "developer":   ("#55efc4", "#2d3436"),
}


def add_participant(g, pid, label, rank_group=None):
    """Add a participant header node."""
    fill, font = COLORS.get(pid, ("#dfe6e9", "#2d3436"))
    g.node(pid, label, shape="box", style="filled,rounded,bold",
           fillcolor=fill, fontcolor=font, fontsize="12", penwidth="2",
           width="1.4", height="0.6")


def add_step(g, step_id, label, color="#0984e3"):
    """Add a step node (small numbered box)."""
    g.node(step_id, label, shape="box", style="filled,rounded",
           fillcolor="#f8f9fa", fontcolor="#2d3436", fontsize="9",
           penwidth="1", width="0", height="0")


def render(g, name):
    """Render to PNG + SVG."""
    for fmt in ["png", "svg"]:
        g.format = fmt
        g.render(filename=os.path.join(OUTPUT_DIR, name), cleanup=True)


# ─── Diagram 1: Happy Path ─────────────────────────────────


def create_happy_path():
    g = graphviz.Digraph("sequence_happy_path", format="png")
    g.attr(
        rankdir="TB",
        bgcolor="#ffffff",
        fontname=FONT,
        fontsize="18",
        label="Happy Path — PR Creation to Merge",
        labelloc="t",
        pad="0.6",
        nodesep="0.6",
        ranksep="0.5",
        dpi="150",
    )
    g.attr("node", fontname=FONT, fontsize="10")
    g.attr("edge", fontname=FONT, fontsize="8")

    # Participants in a row
    participants = [
        ("codegenie", "CodeGenie"),
        ("github", "GitHub"),
        ("car_bridge", "Car Bridge"),
        ("event_proc", "Event\nProcessor"),
        ("datastore", "Data Store"),
        ("policy_bot", "Policy\nBot"),
        ("approver_bot", "Approver\nBot"),
        ("automerge", "Automerge\nBot"),
    ]

    with g.subgraph() as s:
        s.attr(rank="same")
        for pid, label in participants:
            add_participant(s, pid, label)
        # Invisible edges to enforce ordering
        for i in range(len(participants) - 1):
            s.edge(participants[i][0], participants[i + 1][0],
                   style="invis", weight="10")

    # Steps
    steps = [
        ("codegenie", "github",      "1. Create PR", "#0984e3"),
        ("github",    "car_bridge",   "2. PR opened webhook", "#0984e3"),
        ("car_bridge","event_proc",   "3. Route event", "#0984e3"),
        ("event_proc","datastore",     "4. State → CREATED", "#a29bfe"),
        ("github",    "car_bridge",   "5. check_suite.completed", "#0984e3"),
        ("event_proc","datastore",     "6. State → CHECKS_PASSED", "#55efc4"),
        ("policy_bot","github",       "7. Policy evaluation", "#0984e3"),
        ("event_proc","datastore",     "8. State → POLICY_PASSED", "#55efc4"),
        ("approver_bot","github",     "9. Approval review", "#0984e3"),
        ("event_proc","datastore",     "10. State → APPROVED", "#55efc4"),
        ("automerge","github",        "11. Merge PR", "#0984e3"),
        ("event_proc","datastore",     "12. State → MERGED ✓", "#00b894"),
    ]

    prev_step = None
    for i, (src, dst, label, color) in enumerate(steps):
        step_id = f"step_{i}"
        g.node(step_id, label, shape="plaintext", fontsize="9", fontcolor=color)
        g.edge(src, step_id, style="invis", weight="1")
        g.edge(step_id, dst, color=color, penwidth="1.5",
               arrowhead="vee", arrowsize="0.7")
        if prev_step:
            g.edge(prev_step, step_id, style="invis", weight="5")
        prev_step = step_id

    return g


# ─── Diagram 2: Self-Healing Sequence ──────────────────────


def create_self_healing():
    g = graphviz.Digraph("sequence_self_healing", format="png")
    g.attr(
        rankdir="TB",
        bgcolor="#ffffff",
        fontname=FONT,
        fontsize="18",
        label="Self-Healing — Transient CI Failure Recovery",
        labelloc="t",
        pad="0.6",
        nodesep="0.5",
        ranksep="0.5",
        dpi="150",
    )
    g.attr("node", fontname=FONT, fontsize="10")
    g.attr("edge", fontname=FONT, fontsize="8")

    participants = [
        ("scheduler", "Scheduler"),
        ("reconciler", "Reconciler"),
        ("datastore", "Data Store"),
        ("github_api", "GitHub\nAPI"),
        ("classifier", "Classification\nEngine"),
        ("cmd_queue", "Command\nQueue"),
        ("car_bridge", "Car Bridge"),
        ("jenkins", "Jenkins"),
    ]

    with g.subgraph() as s:
        s.attr(rank="same")
        for pid, label in participants:
            add_participant(s, pid, label)
        for i in range(len(participants) - 1):
            s.edge(participants[i][0], participants[i + 1][0],
                   style="invis", weight="10")

    steps = [
        ("scheduler",  "reconciler",   "1. Trigger run",                "#d63031"),
        ("reconciler", "datastore",      "2. Query stale PRs",            "#d63031"),
        ("datastore",   "reconciler",    "3. PR #42: CHECKS_FAILED\n    (30m stale)", "#fdcb6e"),
        ("reconciler", "github_api",    "4. Poll actual state",          "#2d3436"),
        ("github_api", "reconciler",    "5. Confirms: failed,\n    no conflicts",    "#2d3436"),
        ("reconciler", "classifier",    "6. Classify PR #42",            "#e84393"),
        ("classifier", "reconciler",    "7. → RETRY_CHECKS\n    (transient)",       "#e84393"),
        ("reconciler", "datastore",      "8. Check budget:\n    rebuild 0/3",        "#fdcb6e"),
        ("reconciler", "cmd_queue",     "9. Emit: /rebuild #42",         "#e17055"),
        ("cmd_queue",  "car_bridge",    "10. Deliver command",           "#6c5ce7"),
        ("car_bridge", "jenkins",       "11. Trigger rebuild",           "#636e72"),
        ("reconciler", "datastore",      "12. Update: CHECKS_RUNNING\n     rebuild=1", "#74b9ff"),
    ]

    prev_step = None
    for i, (src, dst, label, color) in enumerate(steps):
        step_id = f"sh_step_{i}"
        style = "dashed" if i == 8 else "solid"  # highlight the remediation command
        g.node(step_id, label, shape="plaintext", fontsize="9", fontcolor=color)
        g.edge(src, step_id, style="invis", weight="1")
        g.edge(step_id, dst, color=color, penwidth="1.5" if i != 8 else "2.5",
               style=style, arrowhead="vee", arrowsize="0.7")
        if prev_step:
            g.edge(prev_step, step_id, style="invis", weight="5")
        prev_step = step_id

    return g


# ─── Diagram 3: Command Queue Sequence ─────────────────────


def create_command_queue():
    g = graphviz.Digraph("sequence_command_queue", format="png")
    g.attr(
        rankdir="TB",
        bgcolor="#ffffff",
        fontname=FONT,
        fontsize="18",
        label="Command Queue — Developer Triggers /rebuild",
        labelloc="t",
        pad="0.6",
        nodesep="0.5",
        ranksep="0.5",
        dpi="150",
    )
    g.attr("node", fontname=FONT, fontsize="10")
    g.attr("edge", fontname=FONT, fontsize="8")

    participants = [
        ("developer", "Developer"),
        ("github", "GitHub"),
        ("car_bridge", "Car Bridge"),
        ("cmd_queue", "Command\nQueue"),
        ("jenkins", "Jenkins"),
        ("datastore", "Data Store"),
    ]

    with g.subgraph() as s:
        s.attr(rank="same")
        for pid, label in participants:
            add_participant(s, pid, label)
        for i in range(len(participants) - 1):
            s.edge(participants[i][0], participants[i + 1][0],
                   style="invis", weight="10")

    steps = [
        ("developer", "github",     "1. Comment: /rebuild",      "#55efc4"),
        ("github",    "car_bridge", "2. issue_comment webhook",  "#2d3436"),
        ("car_bridge","car_bridge", "3. Detect slash command",   "#6c5ce7"),
        ("car_bridge","cmd_queue",  "4. Emit command message",   "#6c5ce7"),
        ("cmd_queue", "car_bridge", "5. Deliver for processing", "#6c5ce7"),
        ("car_bridge","car_bridge", "6. Validate: PR open,\n    state allows rebuild", "#6c5ce7"),
        ("car_bridge","jenkins",    "7. Trigger rebuild",        "#636e72"),
        ("car_bridge","datastore",   "8. Log: COMMAND_RECEIVED",  "#fdcb6e"),
    ]

    prev_step = None
    for i, (src, dst, label, color) in enumerate(steps):
        step_id = f"cq_step_{i}"
        g.node(step_id, label, shape="plaintext", fontsize="9", fontcolor=color)
        g.edge(src, step_id, style="invis", weight="1")
        g.edge(step_id, dst, color=color, penwidth="1.5",
               arrowhead="vee", arrowsize="0.7")
        if prev_step:
            g.edge(prev_step, step_id, style="invis", weight="5")
        prev_step = step_id

    return g


def main():
    for name, creator in [
        ("sequence_happy_path", create_happy_path),
        ("sequence_self_healing", create_self_healing),
        ("sequence_command_queue", create_command_queue),
    ]:
        g = creator()
        render(g, name)


if __name__ == "__main__":
    main()
