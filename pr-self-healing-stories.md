# Self-Healing PR Reconciliation System — User Stories

## Epic: Build a self-healing reconciliation system for CodeGenie PRs that detects stale states via event-driven updates and a scheduled reconciler, and automatically remediates transient failures.

---

## Phase 1: Baseline Metrics & Problem Quantification

### Story 1.1 — Identify and Catalog Stale PR Failure Modes
**As a** principal engineer,
**I want to** manually audit a sample of stale/failed CodeGenie PRs from the past 90 days,
**so that** I can categorize the failure modes and understand the distribution of root causes.

**Acceptance Criteria:**
- Sample of at least 50 stale or failed CodeGenie PRs reviewed
- Each PR categorized by failure mode: transient CI failure (timeout, infra), branch behind base, merge conflict, Policy Bot missed/stale, Approver Bot missed, Automerge Bot missed, genuine code issue, other
- Distribution of failure modes documented (e.g., 40% transient CI, 25% branch behind, etc.)
- Identify which failure modes are automatable vs. require human judgment

### Story 1.2 — Measure Current Manual Remediation Effort
**As a** principal engineer,
**I want to** quantify how much time is currently spent manually remediating stale CodeGenie PRs,
**so that** I have a baseline cost to compare against the automated solution.

**Acceptance Criteria:**
- Data collected on: number of stale PRs per week/month requiring manual intervention, average time to detect a stale PR (time from stall to human noticing), average time to remediate per failure mode, who is doing the remediation and their role/cost level
- Time tracking covers a minimum 4-week observation window (or retroactive analysis from logs/Slack)
- Total monthly hours spent on manual remediation calculated
- Cost estimated using fully-loaded hourly rate of engineers involved

### Story 1.3 — Measure Vulnerability Exposure Window
**As a** principal engineer,
**I want to** measure how long vulnerabilities remain unpatched due to stale PRs,
**so that** I can quantify the security risk cost of delayed remediation.

**Acceptance Criteria:**
- For sampled stale PRs, measure: time from PR creation to eventual merge (or abandonment), time the PR was stalled before human intervention, delta between actual merge time and what it would have been without the stall
- Average additional exposure time per vulnerability calculated
- Breakdown by severity (critical, high, medium, low) to weight risk impact
- Number of vulnerabilities that were never patched because the PR was abandoned

### Story 1.4 — Establish Success Metrics and Targets
**As a** principal engineer,
**I want to** define the key metrics that will measure the success of the self-healing system,
**so that** we have clear, quantifiable goals to evaluate the POC and full build against.

**Acceptance Criteria:**
- Metrics defined with baseline values and targets:
  - **PR Throughput Rate**: % of CodeGenie PRs that reach merge without human intervention (baseline vs. target)
  - **Mean Time to Merge (MTTM)**: average time from PR creation to merge (baseline vs. target)
  - **Stale PR Rate**: % of PRs that exceed staleness threshold (baseline vs. target of near-zero)
  - **Mean Time to Remediate (MTTR)**: average time from stall detection to resolution (baseline manual vs. target automated)
  - **Vulnerability Exposure Window**: average time vulnerability remains unpatched (baseline vs. target)
  - **Manual Intervention Rate**: number of PRs requiring human touch per month (baseline vs. target)
  - **False Positive Rate**: remediation actions taken unnecessarily (target < 5%)
- Metrics collection method documented for each (how we'll measure during POC and post-release)

---

## Phase 2: Design & Architecture

### Story 2.1 — System Architecture Design
**As a** principal engineer,
**I want to** document the architecture for the self-healing PR reconciliation system,
**so that** the team has a shared understanding of components, data flow, and integration points.

**Acceptance Criteria:**
- Architecture diagram covering: GitHub webhooks → SNS/SQS → Event Processor → PR State Table → Reconciler → Remediation Actions
- Documented design decisions for event sourcing, state machine, reconciliation loop, and saga/compensation patterns
- Identified integration points with existing systems (CodeGenie, Policy Bot, Approver Bot, Automerge Bot, scheduler)
- DynamoDB table schemas defined for PR State Table and PR Events Table
- Documented state machine with all valid states, transitions, and per-state staleness thresholds
- Remediation strategy matrix mapping each stale state to its corrective action
- Retry budget and escalation policy documented
- Circuit breaker thresholds defined

---

## Phase 3: Proof of Concept

### Story 3.1 — POC: Lightweight State Tracking Script
**As a** developer,
**I want to** build a lightweight script that polls GitHub for all open CodeGenie PRs and classifies their current state,
**so that** I can validate the state classification logic without building the full event-driven pipeline.

**Acceptance Criteria:**
- Script queries GitHub API for all open PRs created by CodeGenie across target repositories
- For each PR, script determines: current check status, whether branch is behind base, whether merge conflicts exist, Policy Bot status, Approver Bot status, time since last activity
- Script classifies each PR into one of the defined states (CHECKS_RUNNING, CHECKS_FAILED, AWAITING_POLICY, etc.)
- Script identifies stale PRs and outputs the recommended remediation action for each
- Output is a structured report (JSON or CSV) that can be reviewed manually
- Script runs on-demand and completes within a reasonable time (< 5 minutes for all target repos)

### Story 3.2 — POC: Automated Remediation for Top 2 Failure Modes
**As a** developer,
**I want to** implement automated remediation for the two most common failure modes identified in Phase 1,
**so that** I can prove the concept works and measure its effectiveness on the highest-impact scenarios.

**Acceptance Criteria:**
- Based on Phase 1 data, the two most common automatable failure modes are selected (likely: transient CI failure → rebuild, and branch behind → update branch)
- POC script extends Story 3.1 to automatically execute remediation for these two cases
- Remediation actions are gated by a confirmation flag (dry-run by default, opt-in to execute)
- Script logs every action taken with PR number, classification, action, and outcome
- Script runs daily via a cron job or manual trigger for a 2-week trial period
- Guard rails: retry budget of 1 attempt per PR per action type, no close-and-reopen

### Story 3.3 — POC: Collect POC Metrics
**As a** developer,
**I want to** collect metrics during the POC trial period,
**so that** I can compare POC performance against the baseline and project full-build ROI.

**Acceptance Criteria:**
- During the 2-week POC period, the following metrics are tracked:
  - Number of stale PRs detected per day
  - Number of automated remediations attempted (by type)
  - Number of successful remediations (PR progressed to next state)
  - Number of failed remediations (action didn't resolve the stall)
  - Number of PRs that still required manual intervention despite POC
  - Time savings: estimated time saved per successful automated remediation
- Metrics are compared against Phase 1 baselines
- Report generated summarizing POC findings and effectiveness

---

## Phase 4: ROI Analysis & Business Case

### Story 4.1 — Calculate Direct Cost Savings (Engineer Time)
**As a** principal engineer,
**I want to** calculate the direct cost savings from automating PR remediation,
**so that** I can justify the development investment with concrete dollar figures.

**Acceptance Criteria:**
- Calculation uses baseline data from Phase 1 and POC results from Phase 3
- Formula documented:
  - `Monthly manual hours` × `fully-loaded hourly rate` = `current monthly cost`
  - `% of manual hours eliminated by automation` (from POC data, extrapolated to full build) = `projected monthly savings`
  - `Annual savings` = `monthly savings` × 12
- Accounts for the fact that full build will cover more failure modes than the POC
- Includes estimate of hours currently spent by different role levels (e.g., senior engineer vs. staff)
- Context switching cost estimated (each manual remediation interrupts deep work — apply a multiplier for context switch overhead, typically 1.5–2x the raw time)

### Story 4.2 — Calculate Security Risk Reduction Value
**As a** principal engineer,
**I want to** quantify the security value of faster vulnerability remediation,
**so that** the ROI includes risk reduction beyond just engineer time savings.

**Acceptance Criteria:**
- Calculation uses vulnerability exposure window data from Phase 1
- Projected reduction in exposure window based on POC MTTM improvements
- Value framed in terms the business understands:
  - Reduction in average days a known vulnerability remains unpatched
  - Number of additional vulnerabilities fully remediated per month (PRs that would have been abandoned)
  - Alignment with SLA/compliance requirements for vulnerability remediation timelines (if applicable)
- Risk reduction expressed both qualitatively (reduced attack surface narrative) and quantitatively where possible

### Story 4.3 — Calculate Development Cost and Payback Period
**As a** principal engineer,
**I want to** estimate the full build cost and calculate the payback period,
**so that** leadership can see when the investment breaks even.

**Acceptance Criteria:**
- Development cost estimated: story points or engineering weeks for Phases 5–12 (full build), broken down by phase
- Accounts for: development time, testing, code review, deployment, observation period, ongoing maintenance (estimated hours/month)
- Payback period calculated: `total development cost` ÷ `monthly savings` = months to break even
- ROI calculated: `(annual savings − annualized development cost) ÷ annualized development cost` × 100
- Sensitivity analysis: best case, expected case, worst case scenarios (varying automation success rate)

### Story 4.4 — Compile ROI Presentation
**As a** principal engineer,
**I want to** compile the metrics, POC results, and ROI analysis into a presentation for stakeholders,
**so that** I can secure approval and prioritization for the full build.

**Acceptance Criteria:**
- Presentation includes: problem statement with baseline metrics, POC results and demonstrated effectiveness, projected ROI with direct savings and security value, development cost estimate and payback period, risk/sensitivity analysis, proposed timeline for full build
- Key metrics presented visually (before/after charts, projected savings over time)
- Clear ask defined: engineering investment needed, expected timeline, success criteria

---

## Phase 5: PR State Table & Event Ingestion

### Story 5.1 — Create PR State Table (DynamoDB)
**As a** developer,
**I want to** create a DynamoDB table that tracks the current state of all active CodeGenie PRs,
**so that** the reconciler has a reliable source of truth for identifying stale PRs.

**Acceptance Criteria:**
- PR State Table created via CloudFormation with schema: `pr_number` (PK), `repo`, `branch`, `current_state`, `last_event_timestamp`, `retry_counts` (map), `created_at`, `ttl`
- Table has appropriate read/write capacity or on-demand billing configured
- GSI on `current_state` + `last_event_timestamp` to support stale PR queries
- TTL attribute enabled on the table for automatic cleanup of terminal records

### Story 5.2 — Create PR Events Table (DynamoDB)
**As a** developer,
**I want to** create an append-only event log table for PR lifecycle events,
**so that** the reconciler can reason about what happened (and what didn't) in a PR's lifecycle.

**Acceptance Criteria:**
- PR Events Table created via CloudFormation with schema: `pr_number` (PK) + `event_timestamp` (SK), `event_type`, `source`, `payload`
- TTL attribute enabled with configurable retention period (default 30 days)
- Table supports efficient queries for all events of a given PR in chronological order

### Story 5.3 — Extend Webhook Event Processor to Update PR State Table
**As a** developer,
**I want to** extend the existing GitHub webhook event processor to write state updates to the PR State Table,
**so that** incoming GitHub events are the primary driver of PR state.

**Acceptance Criteria:**
- Event processor handles the following GitHub events and maps them to state transitions: `pull_request.opened` → CREATED, `check_suite.completed` → CHECKS_PASSED / CHECKS_FAILED, Policy Bot status update → POLICY_PASSED / POLICY_FAILED, `pull_request_review.submitted` (Approver Bot) → APPROVED, `pull_request.closed` (merged) → MERGED, `pull_request.closed` (not merged) → CLOSED
- Each event is written to both the PR State Table (update current state) and PR Events Table (append event)
- Event processor is idempotent — duplicate webhook deliveries produce the same state
- Late-arriving events for PRs in terminal state (MERGED/CLOSED) are ignored gracefully
- Events for unknown PRs that are not `pull_request.opened` are ignored gracefully
- `last_event_timestamp` is updated on every state transition

### Story 5.4 — Implement Soft Delete with TTL on PR Close/Merge
**As a** developer,
**I want to** set a TTL on PR State Table records when a PR reaches a terminal state,
**so that** the table stays lean with only active PRs while allowing a grace period for late events.

**Acceptance Criteria:**
- When `current_state` is set to MERGED or CLOSED, `ttl` is set to `now + 24 hours` (epoch seconds)
- DynamoDB TTL automatically deletes expired records
- Reconciler query excludes records in MERGED/CLOSED state
- Event processor checks for terminal state before processing and ignores late events

---

## Phase 6: State Machine & Classification Engine

### Story 6.1 — Implement PR Lifecycle State Machine
**As a** developer,
**I want to** implement a formal state machine that defines valid PR states and transitions,
**so that** the system can detect anomalous states and enforce valid transitions.

**Acceptance Criteria:**
- State machine defines all valid states: CREATED, CHECKS_RUNNING, CHECKS_PASSED, CHECKS_FAILED, POLICY_EVALUATING, POLICY_PASSED, POLICY_FAILED, APPROVED, MERGING, MERGED, CLOSED, NEEDS_INTERVENTION
- Each state has a defined staleness threshold (configurable)
- Invalid state transitions are logged and flagged but do not crash the system
- State machine is a reusable component that can be unit tested independently

### Story 6.2 — Implement Stale PR Classification Engine
**As a** developer,
**I want to** build a classification engine that examines a stale PR and determines the appropriate remediation action,
**so that** the reconciler can dispatch the correct fix for each stuck PR.

**Acceptance Criteria:**
- Classification engine takes current PR state, event history, and live GitHub state as inputs
- Produces one of the following classifications: UPDATE_BRANCH (branch is behind base), RETRY_CHECKS (checks failed with transient signal — timeout, infra error), RETRIGGER_POLICY_BOT (policy bot hasn't run or stale), RETRIGGER_APPROVER_BOT (policy passed but no approval event), RETRIGGER_MERGE (approved but automerge didn't fire), CLOSE_AND_REOPEN (merge conflicts), NEEDS_INTERVENTION (max retries exceeded or unrecognized failure), NO_ACTION (still within staleness window or already in progress)
- Classification is deterministic and order-independent — same inputs always produce same output
- Classification logic is unit tested for each scenario

---

## Phase 7: Remediation Strategies

### Story 7.1 — Implement Update Branch Strategy
**As a** developer,
**I want to** implement a remediation strategy that updates a PR branch when it falls behind base,
**so that** stale branches are automatically brought up to date.

**Acceptance Criteria:**
- Strategy calls GitHub API to update the PR branch (merge base into head)
- Strategy is idempotent — safe to call if branch is already up to date
- Retry count for `branch_update` is incremented in the PR State Table
- Strategy respects retry budget (default: 2 attempts) before escalating
- State transitions back to CHECKS_RUNNING after successful branch update

### Story 7.2 — Implement Retry Checks / Rebuild Strategy
**As a** developer,
**I want to** implement a remediation strategy that retriggers failed checks when the failure was transient,
**so that** infrastructure flakiness doesn't permanently block PRs.

**Acceptance Criteria:**
- Strategy verifies checks are not currently running before retriggering
- Strategy retriggers the appropriate CI system (Jenkins rebuild)
- Retry count for `rebuild` is incremented in the PR State Table
- Strategy respects retry budget (default: 3 attempts) before escalating
- Transient failure signals are configurable (e.g., timeout, connection error, infrastructure error patterns)

### Story 7.3 — Implement Retrigger Bot Strategies
**As a** developer,
**I want to** implement remediation strategies that retrigger Policy Bot, Approver Bot, or Automerge Bot when they fail to act,
**so that** missed webhook events don't permanently stall the pipeline.

**Acceptance Criteria:**
- Each bot retrigger strategy uses the appropriate mechanism (label toggle, comment event, API call) to re-invoke the bot
- Each strategy is idempotent and safe to call multiple times
- Retry counts are tracked independently per bot type
- Retry budgets are configurable per bot (default: 2 attempts each)

### Story 7.4 — Implement Close and Reopen Strategy
**As a** developer,
**I want to** implement a remediation strategy that closes a conflicted PR and opens a fresh one,
**so that** merge conflicts are resolved by regenerating the PR from a clean branch.

**Acceptance Criteria:**
- Strategy closes the existing PR with a comment explaining the reason
- Strategy creates a new branch from the latest base and regenerates the fix (delegates to CodeGenie's existing PR creation logic)
- Strategy includes a guard to prevent duplicate PRs (checks for existing open PR for the same vulnerability before creating)
- Old PR number is recorded in the new PR's event history for traceability
- Retry budget: 1 attempt before escalating to NEEDS_INTERVENTION
- New PR gets a fresh record in the PR State Table; old PR record enters TTL cleanup

---

## Phase 8: Reconciler & Scheduler Integration

### Story 8.1 — Implement Reconciler Core Logic
**As a** developer,
**I want to** build the reconciler that queries the PR State Table for stale PRs and dispatches remediation,
**so that** stuck PRs are automatically detected and healed.

**Acceptance Criteria:**
- Reconciler queries PR State Table for records where `current_state` is not terminal and `last_event_timestamp` is older than the state's staleness threshold
- For each stale PR, reconciler polls the GitHub API to get actual current state (trust but verify)
- If actual state differs from table state (missed event), reconciler updates the table and re-evaluates
- If still stale after refresh, reconciler invokes the classification engine and dispatches the appropriate remediation strategy
- All remediation actions are logged to the PR Events Table with `source = reconciler`

### Story 8.2 — Implement Circuit Breaker
**As a** developer,
**I want to** implement a circuit breaker that detects systemic failures across multiple PRs,
**so that** the reconciler backs off during infrastructure outages instead of flooding the system with retries.

**Acceptance Criteria:**
- Circuit breaker tracks remediation failure rate over a sliding window (e.g., last 15 minutes)
- If failure rate exceeds threshold (e.g., >50% of actions failing), circuit breaker trips and reconciler pauses remediation
- Circuit breaker has a half-open state that allows a single probe action after a cooldown period
- Circuit breaker state is logged and triggers an alert/notification when tripped

### Story 8.3 — Integrate Reconciler into Existing Scheduler
**As a** developer,
**I want to** extend the existing CodeGenie scheduler to run the reconciler after its PR creation cycle,
**so that** self-healing runs on the same cadence without requiring new infrastructure.

**Acceptance Criteria:**
- Scheduler executes reconciler logic after completing its existing PR creation responsibilities
- Reconciler execution is independent — failure in the reconciler does not affect PR creation
- Reconciler execution time is bounded (timeout after configurable max duration)
- Scheduler logs clearly delineate PR creation activity from reconciler activity

---

## Phase 9: Command Queue & Admin API

### Story 9.1 — Implement Command Queue
**As a** developer,
**I want to** create a command queue that accepts remediation commands from multiple sources,
**so that** humans, the Admin API, and the reconciler all trigger actions through a single decoupled pathway.

**Acceptance Criteria:**
- Command queue accepts structured command messages with: `pr_number`, `repo`, `command`, `source` (pr-comment, admin-api, reconciler), `requested_by`, `timestamp`
- Supported commands: `/rebuild`, `/recheck-policy`, `/recheck-sod`, `/recheck-approval`, `/merge`, `/update-branch`, `/close-and-reopen`, `/cancel`
- Queue provides backpressure — commands are processed sequentially or with controlled concurrency
- Invalid or malformed commands are rejected and logged without crashing the consumer
- Every command processed is logged to the PR Events Table with `event_type = COMMAND_RECEIVED`

### Story 9.2 — Extend Car Bridge to Route Commands
**As a** developer,
**I want to** extend the Car Bridge lambda to consume the command queue and route commands to the appropriate bot or API,
**so that** there is a single routing layer for all remediation actions regardless of source.

**Acceptance Criteria:**
- Car Bridge consumes messages from the command queue
- Before routing, Car Bridge validates: PR is still open, command is valid for the PR's current state (e.g., `/merge` rejected if checks haven't passed), requester has permission (for Admin API sourced commands)
- Routing rules:
  - `/rebuild` → triggers Jenkins rebuild
  - `/recheck-policy` → emits event that triggers Policy Bot
  - `/recheck-sod` → emits event that triggers SOD Validator
  - `/recheck-approval` → emits event that triggers Approver Bot
  - `/merge` → emits event that triggers Automerge Bot
  - `/update-branch` → calls GitHub API to merge base into head
  - `/close-and-reopen` → closes PR via GitHub API + delegates new PR creation to CodeGenie
  - `/cancel` → closes PR via GitHub API, sets state to CLOSED
- Invalid commands return a descriptive error logged to Events Table
- Car Bridge is idempotent — processing the same command twice does not cause duplicate side effects

### Story 9.3 — Implement Slash Command Detection from PR Comments
**As a** developer,
**I want to** detect slash commands in PR comments and emit them to the command queue,
**so that** users can trigger remediation actions directly from a PR without needing API access.

**Acceptance Criteria:**
- Car Bridge detects `issue_comment` webhook events containing recognized slash commands (e.g., `/rebuild`, `/recheck-sod`)
- Slash commands are parsed from the comment body (must be at the start of a line)
- Parsed command is emitted to the command queue with `source = pr-comment` and `requested_by = comment author`
- Unrecognized slash commands are ignored (no error, no queue emission)
- Bot replies on the PR with a confirmation comment (e.g., "Rebuild triggered by @danny") or error if command is invalid for current state

### Story 9.4 — Implement CodeGenie Admin API
**As a** developer,
**I want to** create an Admin API within CodeGenie that provides programmatic access to the command queue and system state,
**so that** engineers can inspect, trigger, and manage remediation without commenting on PRs.

**Acceptance Criteria:**
- Endpoints implemented:
  - `POST /api/pr/{repo}/{pr_number}/command` — emits a command to the queue (body: `{ "command": "/rebuild" }`)
  - `GET /api/pr/{repo}/{pr_number}/status` — returns current state, event history, retry counts from State Table and Events Table
  - `GET /api/prs/stale` — returns all PRs currently considered stale
  - `POST /api/reconciler/run` — triggers an on-demand reconciler run outside of the scheduler
  - `POST /api/circuit-breaker/reset` — manually resets circuit breaker to CLOSED state
- All endpoints require authentication (API key or service account)
- Command endpoint validates the command string before emitting to queue
- All API calls are logged for audit trail

### Story 9.5 — Connect Reconciler to Command Queue
**As a** developer,
**I want to** update the reconciler to dispatch remediation actions via the command queue instead of executing them directly,
**so that** all remediation flows through the same routing and validation path regardless of trigger source.

**Acceptance Criteria:**
- Reconciler emits command messages to the command queue with `source = reconciler`
- Reconciler no longer directly calls GitHub API or bot APIs for remediation
- Car Bridge processes reconciler commands identically to human or Admin API commands
- Retry counting and state updates still happen in the reconciler after command dispatch
- If command queue is unavailable, reconciler logs the failure and counts it toward circuit breaker

---

## Phase 10: Observability & Alerting

### Story 10.1 — Implement Reconciler Metrics and Logging
**As a** developer,
**I want to** add structured logging and CloudWatch metrics for all reconciler activity,
**so that** we can monitor self-healing effectiveness and tune thresholds.

**Acceptance Criteria:**
- Structured log entries for every reconciler action: PR number, classified state, action taken, outcome (success/failure)
- CloudWatch metrics emitted for: stale PRs detected per run, remediation actions dispatched (by type), remediation success/failure rate, circuit breaker state changes, PRs escalated to NEEDS_INTERVENTION
- Dashboard created showing reconciler health and effectiveness over time

### Story 10.2 — Implement Escalation Notifications
**As a** developer,
**I want to** receive notifications when a PR is escalated to NEEDS_INTERVENTION,
**so that** a human can investigate PRs that the system cannot self-heal.

**Acceptance Criteria:**
- When a PR transitions to NEEDS_INTERVENTION, a notification is sent (Slack, email, or SNS — configurable)
- Notification includes: PR link, repository, vulnerability details, event history summary, actions attempted and their outcomes
- Circuit breaker trips also generate a notification with summary of systemic failure

### Story 10.3 — Implement Ongoing Success Metrics Dashboard
**As a** developer,
**I want to** build a dashboard that continuously tracks the success metrics defined in Phase 1,
**so that** we can demonstrate ongoing value and detect regressions.

**Acceptance Criteria:**
- Dashboard displays all metrics from Story 1.4 with current values vs. baseline vs. targets:
  - PR Throughput Rate (% merged without human intervention)
  - Mean Time to Merge (MTTM)
  - Stale PR Rate
  - Mean Time to Remediate (MTTR)
  - Vulnerability Exposure Window
  - Manual Intervention Rate
  - False Positive Rate
- Dashboard shows trends over time (weekly/monthly)
- Dashboard includes a running ROI tracker: cumulative hours saved, cumulative cost savings
- Data sourced from PR Events Table and CloudWatch metrics

---

## Phase 11: Testing

### Story 11.1 — Unit Tests for State Machine and Classification Engine
**As a** developer,
**I want to** have comprehensive unit tests for the state machine and classification logic,
**so that** I can confidently make changes without breaking remediation behavior.

**Acceptance Criteria:**
- Unit tests cover every valid state transition
- Unit tests cover every classification scenario (one test per remediation type)
- Unit tests verify invalid transitions are handled gracefully
- Unit tests verify retry budget enforcement and escalation to NEEDS_INTERVENTION
- Unit tests for idempotency of event processing (duplicate events)

### Story 11.2 — Integration Tests for Remediation Strategies
**As a** developer,
**I want to** have integration tests that verify each remediation strategy works against the GitHub API,
**so that** I can validate the self-healing actions before release.

**Acceptance Criteria:**
- Integration tests for each strategy using a test repository
- Tests verify: update branch, retry checks, retrigger bots, close and reopen
- Tests verify guard conditions (e.g., don't retrigger checks if already running, don't create duplicate PRs)
- Tests can run in CI with appropriate GitHub token scoping

### Story 11.3 — End-to-End Test for Reconciliation Loop
**As a** developer,
**I want to** validate the full reconciliation loop end-to-end,
**so that** I can verify the system detects stale PRs and heals them in a realistic scenario.

**Acceptance Criteria:**
- E2E test creates a PR, simulates a stale state (e.g., no check result after threshold), and verifies the reconciler detects and remediates it
- E2E test verifies the full lifecycle: event ingestion → state table update → reconciler detection → classification → remediation → state progression
- E2E test verifies soft delete after successful merge

---

## Phase 12: Rollout & Release

### Story 12.1 — Deploy Infrastructure (DynamoDB Tables, CloudFormation Updates)
**As a** developer,
**I want to** deploy the new DynamoDB tables and any CloudFormation stack updates to the target environment,
**so that** the infrastructure is in place before enabling the application logic.

**Acceptance Criteria:**
- PR State Table and PR Events Table deployed via CloudFormation
- IAM permissions updated for event processor and reconciler to read/write tables
- CloudWatch alarms configured for DynamoDB throttling and errors
- Infrastructure deployed to staging first, validated, then promoted to production

### Story 12.2 — Release Event Processor Updates (Observation Mode)
**As a** developer,
**I want to** deploy the extended event processor in observation mode,
**so that** I can verify state tracking accuracy before enabling remediation.

**Acceptance Criteria:**
- Event processor writes to PR State Table and PR Events Table in production
- No remediation actions are taken — reconciler runs in dry-run/log-only mode
- State table accuracy is validated against actual GitHub state for a sample of PRs
- Observation period runs for a minimum of 1 week (or configurable duration)
- Discrepancies between table state and GitHub state are logged and investigated

### Story 12.3 — Enable Reconciler with Conservative Thresholds
**As a** developer,
**I want to** enable the reconciler with conservative staleness thresholds and retry budgets,
**so that** self-healing begins cautiously and can be tuned based on real-world behavior.

**Acceptance Criteria:**
- Reconciler enabled in production with staleness thresholds set to 2x the expected values
- Retry budgets set conservatively (e.g., 1 rebuild, 1 branch update, 0 close-and-reopen initially)
- Close-and-reopen strategy is disabled initially (feature flagged) until simpler strategies are validated
- All remediation actions generate notifications during initial rollout for human review
- Runbook created for disabling the reconciler if issues arise

### Story 12.4 — Tune Thresholds and Enable Full Remediation
**As a** developer,
**I want to** tune staleness thresholds and retry budgets based on observation data and enable the full remediation suite,
**so that** the system operates at optimal efficiency.

**Acceptance Criteria:**
- Staleness thresholds adjusted based on actual pipeline timing data from the observation period
- Retry budgets adjusted based on observed transient failure rates
- Close-and-reopen strategy enabled after simpler strategies have proven stable
- Escalation notifications reduced to only true NEEDS_INTERVENTION cases (no longer notifying on every action)
- Documentation updated with final configuration values and tuning rationale

### Story 12.5 — Post-Release ROI Validation
**As a** principal engineer,
**I want to** validate actual ROI against the projections made in Phase 4 after 30 and 90 days of production operation,
**so that** I can demonstrate realized value and refine future project estimation.

**Acceptance Criteria:**
- 30-day report comparing actual metrics against Phase 4 projections: actual hours saved vs. projected, actual MTTM reduction vs. projected, actual stale PR rate vs. projected, actual manual intervention rate vs. projected
- 90-day report with the same comparisons plus: cumulative cost savings, actual payback period progress vs. projected, identification of any failure modes not covered by the current system (backlog for future iteration)
- Report shared with stakeholders who approved the investment
- Lessons learned documented for future automation projects
