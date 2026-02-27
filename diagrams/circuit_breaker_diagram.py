#!/usr/bin/env python3
"""Circuit Breaker state machine diagram."""

import os
import graphviz

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FONT = "Helvetica Neue,Helvetica,Arial"


def create_circuit_breaker():
    g = graphviz.Digraph("circuit_breaker", format="png")
    g.attr(
        rankdir="LR",
        bgcolor="#ffffff",
        fontname=FONT,
        fontsize="18",
        label="Circuit Breaker State Machine",
        labelloc="t",
        labeljust="c",
        pad="0.8",
        nodesep="2.0",
        ranksep="2.5",
        dpi="150",
    )
    g.attr("node", fontname=FONT, fontsize="12", style="filled,bold", width="1.8", height="1.8", penwidth="3")
    g.attr("edge", fontname=FONT, fontsize="10", penwidth="2.0")

    # States
    g.node("CLOSED", "CLOSED\n\nNormal\nOperation", shape="doublecircle",
           fillcolor="#55efc4", fontcolor="#2d3436", color="#00b894")
    g.node("OPEN", "OPEN\n\nRemediation\nPaused", shape="circle",
           fillcolor="#d63031", fontcolor="#ffffff", color="#9b1b1b")
    g.node("HALF_OPEN", "HALF-OPEN\n\nProbing\n(1 PR)", shape="circle",
           fillcolor="#ffeaa7", fontcolor="#2d3436", color="#fdcb6e")

    # Transitions
    g.edge("CLOSED", "OPEN",
           label="  Failure rate > 50%\n  (min 5 actions in window)  ",
           color="#d63031", fontcolor="#d63031")
    g.edge("OPEN", "HALF_OPEN",
           label="  Cooldown elapsed\n  (10 min)  ",
           color="#fdcb6e", fontcolor="#856404")
    g.edge("HALF_OPEN", "CLOSED",
           label="  Probe succeeds  ",
           color="#00b894", fontcolor="#00b894")
    g.edge("HALF_OPEN", "OPEN",
           label="  Probe fails  ",
           color="#d63031", fontcolor="#d63031")
    g.edge("OPEN", "CLOSED",
           label="  Admin API:\n  /circuit-breaker/reset  ",
           color="#6c5ce7", fontcolor="#6c5ce7", style="dashed")

    return g


def main():
    g = create_circuit_breaker()
    for fmt in ["png", "svg"]:
        g.format = fmt
        g.render(filename=os.path.join(OUTPUT_DIR, "circuit_breaker"), cleanup=True)


if __name__ == "__main__":
    main()
