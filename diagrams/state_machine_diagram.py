#!/usr/bin/env python3
"""PR Lifecycle State Machine diagram — all 12 states with self-healing loops."""

import os
import graphviz

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT = "Helvetica Neue,Helvetica,Arial"

# Colors
INIT_PURPLE = "#a29bfe"
ACTIVE_BLUE = "#74b9ff"
PASS_GREEN = "#55efc4"
FAIL_RED = "#ff7675"
TERMINAL_GREEN = "#00b894"
TERMINAL_GRAY = "#636e72"
ALERT_RED = "#d63031"
EDGE_HAPPY = "#0984e3"
EDGE_FAIL = "#d63031"
EDGE_HEAL_BLUE = "#0984e3"
EDGE_HEAL_ORANGE = "#e17055"
EDGE_REOPEN = "#6c5ce7"
EDGE_ESCALATE = "#9b1b1b"


def create_state_machine():
    g = graphviz.Digraph("pr_state_machine", format="png")
    g.attr(
        rankdir="TB",
        bgcolor="#ffffff",
        fontname=FONT,
        fontsize="20",
        label="PR Lifecycle State Machine — Self-Healing Flow",
        labelloc="t",
        labeljust="c",
        pad="0.6",
        nodesep="0.7",
        ranksep="0.9",
        dpi="150",
        splines="true",
    )
    g.attr("node", fontname=FONT, fontsize="11", style="filled,rounded", shape="box", penwidth="2")
    g.attr("edge", fontname=FONT, fontsize="9")

    # ── States ──────────────────────────────────────────────

    g.node("CREATED", "CREATED\n⏱ stale: 5 min",
           fillcolor=INIT_PURPLE, fontcolor="#ffffff")
    g.node("CHECKS_RUNNING", "CHECKS_RUNNING\n⏱ stale: 60 min",
           fillcolor=ACTIVE_BLUE, fontcolor="#ffffff")
    g.node("CHECKS_PASSED", "CHECKS_PASSED\nwaits for Policy Bot",
           fillcolor=PASS_GREEN, fontcolor="#2d3436")
    g.node("CHECKS_FAILED", "CHECKS_FAILED\n⏱ stale: 30 min",
           fillcolor=FAIL_RED, fontcolor="#ffffff")
    g.node("POLICY_EVALUATING", "POLICY_EVALUATING\n⏱ stale: 30 min\n(can run at any pre-merge stage)",
           fillcolor=ACTIVE_BLUE, fontcolor="#ffffff")
    g.node("POLICY_PASSED", "POLICY_PASSED\n⏱ stale: 15 min",
           fillcolor=PASS_GREEN, fontcolor="#2d3436")
    g.node("POLICY_FAILED", "POLICY_FAILED",
           fillcolor=FAIL_RED, fontcolor="#ffffff")
    g.node("APPROVED", "APPROVED\n⏱ stale: 10 min\n(SOD checked here for 2-approval repos)",
           fillcolor=PASS_GREEN, fontcolor="#2d3436")
    g.node("MERGING", "MERGING\n⏱ stale: 5 min",
           fillcolor=ACTIVE_BLUE, fontcolor="#ffffff")

    # Terminal states — double border
    g.node("MERGED", "MERGED  ✓\nTTL: 24h soft-delete",
           fillcolor=TERMINAL_GREEN, fontcolor="#ffffff", peripheries="2", penwidth="3")
    g.node("CLOSED", "CLOSED\nTTL: 24h soft-delete",
           fillcolor=TERMINAL_GRAY, fontcolor="#ffffff", peripheries="2", penwidth="3")
    g.node("NEEDS_INTERVENTION", "NEEDS INTERVENTION\nawaits human",
           fillcolor=ALERT_RED, fontcolor="#ffffff", peripheries="2", penwidth="3")

    # ── Happy Path (bold blue) ──────────────────────────────

    happy = dict(color=EDGE_HAPPY, fontcolor=EDGE_HAPPY, penwidth="2.5", style="bold")
    g.edge("CREATED", "CHECKS_RUNNING", label="CI checks begin", **happy)
    g.edge("CHECKS_RUNNING", "CHECKS_PASSED", label="All checks pass", **happy)
    g.edge("CHECKS_PASSED", "POLICY_EVALUATING", label="Policy Bot evaluates", **happy)
    g.edge("POLICY_EVALUATING", "POLICY_PASSED", label="All policies met", **happy)
    g.edge("POLICY_PASSED", "APPROVED", label="Approver Bot approves", **happy)
    g.edge("APPROVED", "MERGING", label="Automerge begins", **happy)
    g.edge("MERGING", "MERGED", label="Merge succeeds", **happy)

    # ── Failure Branches (solid red) ────────────────────────

    fail = dict(color=EDGE_FAIL, fontcolor=EDGE_FAIL, penwidth="1.5")
    g.edge("CHECKS_RUNNING", "CHECKS_FAILED", label="Check fails / timeout", **fail)
    g.edge("POLICY_EVALUATING", "POLICY_FAILED", label="Policy violated\n(SOD · foreign commit · etc.)", **fail)

    # ── Merge Failure Paths ─────────────────────────────────

    g.edge("MERGING", "CHECKS_RUNNING", label="Branch behind\n→ auto-update",
           color=EDGE_HEAL_ORANGE, fontcolor=EDGE_HEAL_ORANGE, penwidth="1.5", style="dashed")
    g.edge("MERGING", "CLOSED", label="Merge conflicts",
           color=EDGE_FAIL, fontcolor=EDGE_FAIL, penwidth="1.5")

    # ── Self-Healing: Rebuild / Update Branch (dashed blue) ─

    heal_blue = dict(color=EDGE_HEAL_BLUE, fontcolor=EDGE_HEAL_BLUE, penwidth="1.5", style="dashed")
    g.edge("CHECKS_FAILED", "CHECKS_RUNNING",
           label="🔄 Rebuild (max 3)", **heal_blue)
    g.edge("CHECKS_FAILED", "CHECKS_RUNNING",
           label="🔄 Update Branch (max 2)",
           color=EDGE_HEAL_BLUE, fontcolor=EDGE_HEAL_BLUE, penwidth="1.5", style="dashed",
           constraint="false")

    # ── Self-Healing: Close & Reopen (dashed purple) ────────

    heal_purple = dict(color=EDGE_REOPEN, fontcolor=EDGE_REOPEN, penwidth="1.5", style="dashed")
    g.edge("CHECKS_FAILED", "CLOSED", label="🔄 Close & Reopen\n(max 1 · conflicts)", **heal_purple)
    g.edge("CLOSED", "CREATED", label="New PR created\nfor same vulnerability", **heal_purple)

    # ── Self-Healing: Bot Retriggers (dashed orange) ────────

    heal_orange = dict(color=EDGE_HEAL_ORANGE, fontcolor=EDGE_HEAL_ORANGE, penwidth="1.5", style="dashed")
    g.edge("CHECKS_PASSED", "POLICY_EVALUATING",
           label="🔄 Retrigger Policy Bot (max 2)", constraint="false", **heal_orange)
    g.edge("POLICY_FAILED", "POLICY_EVALUATING",
           label="🔄 Retrigger Policy (max 2)", **heal_orange)
    g.edge("POLICY_FAILED", "POLICY_EVALUATING",
           label="🔄 Recheck SOD (max 1)", constraint="false", **heal_orange)
    g.edge("POLICY_PASSED", "APPROVED",
           label="🔄 Retrigger Approver (max 2)", constraint="false", **heal_orange)
    g.edge("APPROVED", "MERGING",
           label="🔄 Retrigger Automerge (max 2)", constraint="false", **heal_orange)

    # ── Self-Healing: SOD Recheck from APPROVED (dashed orange) ─
    g.edge("APPROVED", "POLICY_EVALUATING",
           label="🔄 Recheck SOD (max 1)\n(2-approval repos)", constraint="false", **heal_orange)

    # ── Permanent Policy Failure → Close (no reopen) ────────

    g.edge("POLICY_FAILED", "CLOSED",
           label="Permanent failure\n(foreign commit · invalid file)\nCodeGenie closes",
           color=EDGE_ESCALATE, fontcolor=EDGE_ESCALATE, penwidth="1.5")

    # ── Escalation (solid dark red) ─────────────────────────

    esc = dict(color=EDGE_ESCALATE, fontcolor=EDGE_ESCALATE, penwidth="1.5")
    g.edge("CHECKS_FAILED", "NEEDS_INTERVENTION",
           label="Persistent failure /\nbudget exhausted", **esc)
    g.edge("POLICY_FAILED", "NEEDS_INTERVENTION",
           label="Unknown failure /\nbudget exhausted", **esc)

    # ── Legend ──────────────────────────────────────────────

    with g.subgraph(name="cluster_legend") as legend:
        legend.attr(
            label="Legend",
            fontname=FONT,
            fontsize="12",
            style="rounded,filled",
            fillcolor="#f8f9fa",
            color="#dee2e6",
            labeljust="l",
        )
        legend.attr("node", shape="plaintext", style="", fontsize="9", width="0", height="0")
        legend.node("L1", "")
        legend.node("L2", "")
        legend.node("L3", "")
        legend.node("L4", "")
        legend.node("L5", "")
        legend.node("L6", "")

        legend.node("LT1", "")
        legend.node("LT2", "")
        legend.node("LT3", "")
        legend.node("LT4", "")
        legend.node("LT5", "")
        legend.node("LT6", "")

        legend.edge("L1", "LT1", label="Happy path", color=EDGE_HAPPY, penwidth="2.5", style="bold", fontcolor=EDGE_HAPPY)
        legend.edge("L2", "LT2", label="Failure branch", color=EDGE_FAIL, penwidth="1.5", fontcolor=EDGE_FAIL)
        legend.edge("L3", "LT3", label="Self-heal: rebuild / update", color=EDGE_HEAL_BLUE, penwidth="1.5", style="dashed", fontcolor=EDGE_HEAL_BLUE)
        legend.edge("L4", "LT4", label="Self-heal: bot retrigger", color=EDGE_HEAL_ORANGE, penwidth="1.5", style="dashed", fontcolor=EDGE_HEAL_ORANGE)
        legend.edge("L5", "LT5", label="Close & reopen", color=EDGE_REOPEN, penwidth="1.5", style="dashed", fontcolor=EDGE_REOPEN)
        legend.edge("L6", "LT6", label="Escalation", color=EDGE_ESCALATE, penwidth="1.5", fontcolor=EDGE_ESCALATE)

    return g


def main():
    g = create_state_machine()
    for fmt in ["png", "svg"]:
        g.format = fmt
        g.render(filename=os.path.join(OUTPUT_DIR, "state_machine"), cleanup=True)


if __name__ == "__main__":
    main()
