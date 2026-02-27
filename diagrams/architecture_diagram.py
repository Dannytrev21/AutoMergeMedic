#!/usr/bin/env python3
"""System Architecture diagram using mingrammer/diagrams with AWS service icons."""

import os

# diagrams library writes output relative to cwd — set it to the output dir
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.chdir(OUTPUT_DIR)

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.integration import SQS, SNS, Eventbridge
from diagrams.generic.database import SQL
from diagrams.aws.management import Cloudwatch
from diagrams.onprem.ci import Jenkins
from diagrams.onprem.vcs import Github

# Try multiple import paths for APIGateway
try:
    from diagrams.aws.network import APIGateway
except ImportError:
    try:
        from diagrams.aws.mobile import APIGateway
    except ImportError:
        from diagrams.aws.compute import Lambda as APIGateway  # fallback


def main():
    graph_attr = {
        "fontsize": "20",
        "fontname": "Helvetica Neue",
        "bgcolor": "#ffffff",
        "pad": "0.8",
        "nodesep": "0.8",
        "ranksep": "1.5",
        "dpi": "150",
    }
    node_attr = {
        "fontsize": "11",
        "fontname": "Helvetica Neue",
    }
    edge_attr = {
        "fontsize": "9",
        "fontname": "Helvetica Neue",
    }

    with Diagram(
        "AutoMergeMedic — System Architecture",
        filename="architecture",
        outformat=["png", "svg"],
        direction="LR",
        show=False,
        graph_attr=graph_attr,
        node_attr=node_attr,
        edge_attr=edge_attr,
    ):
        # ── Event Sources ───────────────────────────────
        with Cluster("Event Sources", graph_attr={
            "bgcolor": "#edf2ff", "color": "#0984e3", "style": "filled,rounded",
            "fontsize": "14", "fontname": "Helvetica Neue",
        }):
            gh = Github("GitHub\nWebhooks")
            comments = Github("PR Comments\n/rebuild /merge")
            admin = APIGateway("Admin API\nGateway")

        # ── Routing Layer ───────────────────────────────
        with Cluster("Routing Layer", graph_attr={
            "bgcolor": "#f3edff", "color": "#6c5ce7", "style": "filled,rounded",
            "fontsize": "14", "fontname": "Helvetica Neue",
        }):
            cmd_queue = SQS("Command\nQueue")
            car_bridge = Lambda("Car Bridge\n(Router)")

        # ── Event Processing ────────────────────────────
        with Cluster("Event Processing", graph_attr={
            "bgcolor": "#edfff8", "color": "#00b894", "style": "filled,rounded",
            "fontsize": "14", "fontname": "Helvetica Neue",
        }):
            event_proc = Lambda("Event\nProcessor")

        # ── Data Layer ──────────────────────────────────
        with Cluster("Data Store", graph_attr={
            "bgcolor": "#fff9e6", "color": "#fdcb6e", "style": "filled,rounded",
            "fontsize": "14", "fontname": "Helvetica Neue",
        }):
            state_table = SQL("PR State\nTable")
            events_table = SQL("PR Events\nTable")

        # ── Self-Healing Engine ─────────────────────────
        with Cluster("Self-Healing Engine", graph_attr={
            "bgcolor": "#ffeded", "color": "#d63031", "style": "filled,rounded",
            "fontsize": "14", "fontname": "Helvetica Neue",
        }):
            scheduler = Eventbridge("Scheduler")
            reconciler = Lambda("Reconciler")
            classifier = Lambda("Classification\nEngine")
            circuit_breaker = Cloudwatch("Circuit\nBreaker")

        # ── Bot Ecosystem ───────────────────────────────
        with Cluster("Bot Ecosystem", graph_attr={
            "bgcolor": "#f5f5f5", "color": "#636e72", "style": "filled,rounded",
            "fontsize": "14", "fontname": "Helvetica Neue",
        }):
            jenkins = Jenkins("Jenkins CI")
            policy_bot = Lambda("Policy\nBot")
            approver_bot = Lambda("Approver\nBot")
            automerge_bot = Lambda("Automerge\nBot")

        # ── Standalone ──────────────────────────────────
        sns = SNS("Escalation\nAlerts")
        cw = Cloudwatch("CloudWatch\nMetrics")

        # ── Edges: Event Ingestion ──────────────────────
        gh >> Edge(label="webhook", color="#0984e3") >> car_bridge
        comments >> Edge(label="slash cmd", color="#0984e3") >> cmd_queue
        admin >> Edge(label="command", color="#0984e3") >> cmd_queue
        cmd_queue >> Edge(color="#6c5ce7") >> car_bridge

        # ── Edges: Processing ───────────────────────────
        car_bridge >> Edge(label="events", color="#00b894") >> event_proc
        event_proc >> Edge(label="update", color="#fdcb6e") >> state_table
        event_proc >> Edge(label="append", color="#fdcb6e") >> events_table

        # ── Edges: Command Dispatch ─────────────────────
        car_bridge >> Edge(label="/rebuild", color="#636e72") >> jenkins
        car_bridge >> Edge(label="/recheck", color="#636e72") >> policy_bot
        car_bridge >> Edge(label="/approve", color="#636e72") >> approver_bot
        car_bridge >> Edge(label="/merge", color="#636e72") >> automerge_bot

        # ── Edges: Self-Healing Loop ────────────────────
        scheduler >> Edge(label="triggers", color="#d63031") >> reconciler
        state_table >> Edge(label="reads stale PRs", color="#d63031", style="dashed") >> reconciler
        reconciler >> Edge(label="classifies", color="#e84393", style="dashed") >> classifier
        reconciler >> Edge(label="checks", color="#e84393", style="dashed") >> circuit_breaker
        reconciler >> Edge(label="remediation\ncmds", color="#d63031", style="bold") >> cmd_queue

        # ── Edges: Bot Feedback ─────────────────────────
        jenkins >> Edge(label="check events", color="#636e72", style="dashed") >> gh
        policy_bot >> Edge(label="status events", color="#636e72", style="dashed") >> gh
        approver_bot >> Edge(label="review events", color="#636e72", style="dashed") >> gh
        automerge_bot >> Edge(label="merge events", color="#636e72", style="dashed") >> gh

        # ── Edges: Notifications / Monitoring ───────────
        reconciler >> Edge(label="escalation", color="#d63031", style="dotted") >> sns
        reconciler >> Edge(label="metrics", color="#636e72", style="dotted") >> cw


if __name__ == "__main__":
    main()
