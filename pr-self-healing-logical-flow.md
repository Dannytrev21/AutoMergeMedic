# Self-Healing PR Reconciliation System — Logical Flow Reference

This document describes the pure logic of the system. No technology decisions — just states, flows, rules, and behavior.

---

## 1. PR Lifecycle States

A CodeGenie PR moves through these states from creation to completion. Each state represents a discrete phase where the PR is waiting for something specific to happen.

```
CREATED
  The PR has been opened by CodeGenie. No checks have started yet.
  Waiting for: CI checks to begin

CHECKS_RUNNING
  Jenkins build and/or other CI checks are actively executing.
  Waiting for: Check results (pass or fail)

CHECKS_PASSED
  All CI checks have completed successfully (Jenkins build green).
  Waiting for: Policy Bot to begin evaluation

CHECKS_FAILED
  One or more CI checks failed.
  Subclassified as:
    TRANSIENT — timeout, infra error, connection failure, Jenkins flakiness
    PERSISTENT — actual code/test failure
  Waiting for: Remediation (retry or escalation)

POLICY_EVALUATING
  Policy Bot is actively evaluating the PR against all policies.
  Waiting for: Policy Bot result

POLICY_PASSED
  Policy Bot has approved — all policies met, SOD validation passed, build verified.
  Waiting for: Approver Bot to issue approval

POLICY_FAILED
  Policy Bot has rejected — one or more policies not met.
  Subclassified by failing policy:
    SOD_FAILURE — separation of duties violation
    BUILD_FAILURE — build policy not met
    BRANCH_PROTECTION_FAILURE — branch protection requirements not met
    OTHER_POLICY_FAILURE
  Waiting for: Remediation or escalation

APPROVED
  Approver Bot has issued an approval (triggered by Policy Bot passing
  with branch protections satisfied).
  Waiting for: Automerge Bot to execute merge

MERGING
  Automerge Bot is attempting to merge the PR.
  Waiting for: Merge result

MERGED (terminal)
  PR has been successfully merged. Record enters TTL cleanup.

CLOSED (terminal)
  PR was closed without merging (either by remediation/reopen or abandoned).
  Record enters TTL cleanup.

NEEDS_INTERVENTION (terminal-ish)
  All automated remediation has been exhausted. Human required.
  Stays in table until human resolves, then transitions to MERGED or CLOSED.
```

---

## 2. State Transition Map

Valid transitions and what triggers them. Any transition not listed here is invalid and should be logged as anomalous.

```
CREATED ──────────────────→ CHECKS_RUNNING
  Trigger: CI checks begin (check_suite.requested or check_run.created event)

CHECKS_RUNNING ───────────→ CHECKS_PASSED
  Trigger: All required checks complete successfully

CHECKS_RUNNING ───────────→ CHECKS_FAILED
  Trigger: Any required check fails or times out

CHECKS_FAILED ────────────→ CHECKS_RUNNING
  Trigger: Rebuild triggered (by reconciler, command queue, or manual)

CHECKS_PASSED ────────────→ POLICY_EVALUATING
  Trigger: Policy Bot begins evaluation

POLICY_EVALUATING ────────→ POLICY_PASSED
  Trigger: Policy Bot reports all policies met

POLICY_EVALUATING ────────→ POLICY_FAILED
  Trigger: Policy Bot reports one or more policies failed

POLICY_FAILED ────────────→ POLICY_EVALUATING
  Trigger: Policy re-evaluation triggered (by reconciler, command, or event)

POLICY_PASSED ────────────→ APPROVED
  Trigger: Approver Bot submits approval review

APPROVED ─────────────────→ MERGING
  Trigger: Automerge Bot initiates merge

MERGING ──────────────────→ MERGED
  Trigger: GitHub confirms merge complete

MERGING ──────────────────→ CHECKS_RUNNING
  Trigger: Merge failed due to branch behind, branch updated, checks restart

MERGING ──────────────────→ CLOSED
  Trigger: Merge failed due to conflicts, PR closed for reopen

Any non-terminal state ───→ CLOSED
  Trigger: PR closed (by remediation reopen strategy or manual close)

Any non-terminal state ───→ NEEDS_INTERVENTION
  Trigger: Retry budgets exhausted for all applicable strategies

Any non-terminal state ───→ CHECKS_RUNNING
  Trigger: Branch updated (new commits reset checks)
```

---

## 3. Required Checks Per State

What must be true for the PR to progress from each state.

```
CREATED → CHECKS_RUNNING
  Required: CI pipeline must be triggered (usually automatic on PR creation)

CHECKS_RUNNING → CHECKS_PASSED
  Required:
    ✓ Jenkins build passes
    ✓ All other configured required status checks pass

CHECKS_PASSED → POLICY_EVALUATING → POLICY_PASSED
  Policy Bot evaluates ALL of the following:
    ✓ SOD Validation — PR author ≠ approver, meets separation of duties rules
    ✓ Jenkins Build — build completed successfully (cross-references check status)
    ✓ Branch Protections — all configured branch protection rules are satisfied
    ✓ Any additional configured policy rules (org-specific)

POLICY_PASSED → APPROVED
  Required:
    ✓ Policy Bot has given approval status
    ✓ Branch protections are applied/satisfied
    ✓ Approver Bot issues approval review (conditional on Policy Bot approval)

APPROVED → MERGING → MERGED
  Required:
    ✓ Approver Bot approval is present
    ✓ All required status checks still passing (no new failures)
    ✓ Branch is up to date with base (no merge conflicts)
    ✓ Automerge Bot executes the merge
```

---

## 4. State Table (Logical Schema)

One record per active PR. Represents current known state.

```
PR State Record:
  pr_number           — unique identifier for the PR
  repo                — repository name
  branch              — head branch name
  base_branch         — target branch (e.g., main)
  vulnerability_id    — the vulnerability this PR remediates (for traceability)
  current_state       — one of the states defined above
  state_substatus     — optional detail (e.g., TRANSIENT vs PERSISTENT for CHECKS_FAILED)
  last_event_timestamp — when the last state-changing event was received
  created_at          — when the PR was first created
  retry_counts        — map tracking attempts per strategy:
                          {
                            rebuild: 0,
                            branch_update: 0,
                            retrigger_policy_bot: 0,
                            retrigger_approver_bot: 0,
                            retrigger_automerge_bot: 0,
                            close_and_reopen: 0
                          }
  last_remediation_at  — when the reconciler last took action on this PR
  remediation_action   — what the last remediation action was
  ttl                  — expiration timestamp (set only on terminal states)
```

---

## 5. Events Table (Logical Schema)

Append-only log of everything that happens to a PR. Never updated, only inserted.

```
PR Event Record:
  pr_number           — which PR this event belongs to
  event_timestamp     — when the event occurred (sort key)
  event_type          — one of:
                          PR_OPENED, PR_CLOSED, PR_MERGED
                          CHECKS_STARTED, CHECKS_PASSED, CHECKS_FAILED
                          POLICY_STARTED, POLICY_PASSED, POLICY_FAILED
                          APPROVAL_GRANTED
                          MERGE_ATTEMPTED, MERGE_SUCCEEDED, MERGE_FAILED
                          REMEDIATION_BRANCH_UPDATE
                          REMEDIATION_REBUILD
                          REMEDIATION_RETRIGGER_POLICY
                          REMEDIATION_RETRIGGER_APPROVER
                          REMEDIATION_RETRIGGER_MERGE
                          REMEDIATION_CLOSE_AND_REOPEN
                          ESCALATED_NEEDS_INTERVENTION
                          COMMAND_RECEIVED
  source              — who/what generated this event:
                          github-webhook, codegenie, policy-bot, approver-bot,
                          automerge-bot, reconciler, command-queue, admin-api
  payload             — event-specific detail (check names, error messages,
                          failure reasons, command text, etc.)
  ttl                 — expiration timestamp for automatic cleanup
```

---

## 6. Classification Engine

The classifier takes a stale PR and determines what's wrong and what to do. It is stateless and deterministic — given the same inputs, it always produces the same output.

**Inputs:**
- Current state from State Table
- Event history from Events Table
- Live state from GitHub API (fetched by reconciler before classification)

**Classification Logic (evaluated in priority order):**

```
1. MERGE CONFLICT DETECTED
   Condition: GitHub reports merge conflicts on the PR
   Classification: CLOSE_AND_REOPEN
   Rationale: Cannot be fixed by retrying; need a fresh branch

2. BRANCH BEHIND BASE
   Condition: GitHub reports head branch is behind base branch,
              AND no merge conflicts
   Classification: UPDATE_BRANCH
   Rationale: Simple catch-up, will retrigger checks

3. CHECKS FAILED — TRANSIENT
   Condition: current_state = CHECKS_FAILED
              AND failure signals match transient patterns
              (timeout, infra error, connection refused, Jenkins agent lost, etc.)
   Classification: RETRY_CHECKS
   Rationale: Not a code problem; retry should succeed

4. CHECKS FAILED — PERSISTENT
   Condition: current_state = CHECKS_FAILED
              AND failure signals do NOT match transient patterns
   Classification: NEEDS_INTERVENTION
   Rationale: Likely a real code issue that automation can't fix

5. POLICY BOT STALE
   Condition: current_state = CHECKS_PASSED or POLICY_EVALUATING
              AND time since last event > policy bot staleness threshold
              AND no policy bot event in event history after checks passed
   Classification: RETRIGGER_POLICY_BOT
   Rationale: Policy Bot likely missed the webhook or silently failed

6. POLICY FAILED — SOD
   Condition: current_state = POLICY_FAILED
              AND substatus = SOD_FAILURE
   Classification: RETRIGGER_SOD_CHECK (via command queue)
   Rationale: SOD failures can be transient (data sync, timing); worth one retry

7. POLICY FAILED — OTHER
   Condition: current_state = POLICY_FAILED
              AND substatus ≠ SOD_FAILURE
   Classification: NEEDS_INTERVENTION
   Rationale: Policy failures (other than SOD timing) usually require human judgment

8. APPROVER BOT STALE
   Condition: current_state = POLICY_PASSED
              AND time since policy passed > approver bot staleness threshold
              AND no approval event in event history after policy passed
   Classification: RETRIGGER_APPROVER_BOT
   Rationale: Approver Bot likely missed the policy pass event

9. AUTOMERGE BOT STALE
   Condition: current_state = APPROVED
              AND time since approval > automerge staleness threshold
              AND no merge attempt event in event history after approval
   Classification: RETRIGGER_MERGE
   Rationale: Automerge Bot likely missed the approval event

10. STILL WITHIN THRESHOLD
    Condition: time since last event < staleness threshold for current state
    Classification: NO_ACTION
    Rationale: Still within normal processing window; don't intervene yet

11. FALLTHROUGH
    Condition: None of the above matched
    Classification: NEEDS_INTERVENTION
    Rationale: Unrecognized state; safer to escalate than guess
```

**After classification, before dispatching:**

```
Check retry budget:
  IF retry_counts[strategy] >= max_retries[strategy]:
    Override classification → NEEDS_INTERVENTION
    Reason: "Retry budget exhausted for {strategy} ({count}/{max})"
```

---

## 7. Retry Budgets

Each remediation strategy has a maximum number of attempts before the PR is escalated to NEEDS_INTERVENTION.

```
Strategy                   Max Retries    Rationale
─────────────────────────  ───────────    ─────────
rebuild (retry checks)     3              CI flakiness may need a few tries
branch_update              2              If it fails twice, something deeper is wrong
retrigger_policy_bot       2              One retry for missed event, one for timing
retrigger_approver_bot     2              Same as policy bot
retrigger_automerge_bot    2              Same pattern
retrigger_sod_check        1              SOD failures are usually real; one retry for timing
close_and_reopen           1              Destructive action; only try once
```

**Budget behavior:**
- Each strategy's count is tracked independently
- Counts reset if the PR naturally progresses to a new state (e.g., rebuild succeeds
  and checks now pass — if checks later fail again, the rebuild count starts fresh
  from that new state entry)
- Counts do NOT reset on reconciler re-evaluation without state change
- When ANY strategy's budget is exhausted AND the PR is still stale, escalate

---

## 8. Staleness Thresholds

How long a PR can sit in each state before the reconciler considers it stale and intervenes.

```
State                  Staleness Threshold    Rationale
─────────────────────  ───────────────────    ─────────
CREATED                5 minutes              Checks should start almost immediately
CHECKS_RUNNING         60 minutes             Builds can be slow but not this slow
CHECKS_FAILED          30 minutes             After a retry, give it time but not forever
POLICY_EVALUATING      30 minutes             Policy Bot should complete quickly
POLICY_PASSED          15 minutes             Approver Bot should react fast
APPROVED               10 minutes             Automerge should be near-instant
MERGING                5 minutes              Merge is a fast operation
NEEDS_INTERVENTION     none (no auto-action)  Waiting for human
```

These are configurable and should be tuned based on observed pipeline timing during the observation period.

---

## 9. Reconciler Loop

The reconciler runs on a schedule (piggybacking on the existing CodeGenie scheduler). Each run follows this exact sequence:

```
RECONCILER RUN:

  STEP 1 — Query for stale PRs
    Query the State Table for all records where:
      - current_state is NOT terminal (not MERGED, CLOSED, or NEEDS_INTERVENTION)
      - last_event_timestamp is older than the staleness threshold for that state
    Result: list of candidate stale PRs

  STEP 2 — Circuit breaker check
    IF circuit breaker is OPEN:
      Log "circuit breaker open, skipping remediation"
      IF cooldown period has elapsed:
        Allow ONE PR through as a probe (half-open)
      ELSE:
        Exit reconciler run
    ELSE:
      Proceed with all candidates

  STEP 3 — For each stale PR (in parallel or serial, configurable):

    STEP 3a — Trust but verify (poll GitHub)
      Fetch the PR's actual current state from GitHub API:
        - PR status (open, closed, merged)
        - Check suite status (pending, success, failure, details of failures)
        - Merge conflict status
        - Branch behind status
        - Review status (approvals present?)
        - Labels and comments (for Policy Bot / Approver Bot signals)

    STEP 3b — Reconcile state drift
      Compare GitHub actual state vs State Table state.
      IF they differ (we missed an event):
        Update the State Table to reflect actual state
        Log the drift: "State drift detected for PR #{n}: table={old}, actual={new}"
        Write a synthetic event to the Events Table:
          event_type = STATE_DRIFT_CORRECTED, source = reconciler
        Re-evaluate: is the PR still stale in its corrected state?
        IF no longer stale:
          Skip this PR (it's fine, we just missed an event)
          Continue to next PR

    STEP 3c — Classify
      Pass to the Classification Engine:
        - Corrected current state
        - Event history
        - Live GitHub state
      Receive back: classification (strategy to apply) or NO_ACTION

    STEP 3d — Check retry budget
      Look up retry_counts for the classified strategy
      IF budget exhausted:
        Transition PR to NEEDS_INTERVENTION
        Log event: ESCALATED_NEEDS_INTERVENTION
        Send escalation notification
        Continue to next PR

    STEP 3e — Execute remediation
      Dispatch to the appropriate remediation strategy
      Log event to Events Table: REMEDIATION_{type}, source = reconciler
      Increment retry_counts[strategy] in State Table
      Update last_remediation_at in State Table

    STEP 3f — Record outcome
      IF remediation action succeeded:
        Update State Table (new state based on action taken)
        Log success
      IF remediation action failed:
        Log failure with error details
        Update circuit breaker failure counter

  STEP 4 — Update circuit breaker
    Calculate failure rate over sliding window
    IF failure rate > threshold:
      Trip circuit breaker to OPEN
      Send circuit breaker notification
      Log "circuit breaker tripped: {failure_rate}% failure rate"
```

---

## 10. Remediation Strategies (Detailed Logic)

### UPDATE_BRANCH
```
  Precondition: Branch is behind base, no merge conflicts
  Action:
    1. Call GitHub API to merge base into head branch
    2. If successful, PR state resets to CHECKS_RUNNING
       (new commits trigger CI)
    3. If fails with conflict, reclassify as CLOSE_AND_REOPEN
  Post-action state: CHECKS_RUNNING (checks will retrigger)
  Idempotent: Yes — if already up to date, API returns success/no-op
```

### RETRY_CHECKS (Rebuild)
```
  Precondition: Checks failed with transient signal, checks not currently running
  Action:
    1. Verify checks are not currently in progress (guard against double-trigger)
    2. If checks are running, take NO_ACTION (classify as not-stale-yet)
    3. Trigger Jenkins rebuild (via API, or push empty commit, or re-request checks)
  Post-action state: CHECKS_RUNNING
  Idempotent: Yes — retriggering while already running is a no-op (due to guard)
```

### RETRIGGER_POLICY_BOT
```
  Precondition: Checks passed but Policy Bot hasn't evaluated
  Action:
    1. Use whatever mechanism triggers Policy Bot re-evaluation
       (label toggle, comment event, status event re-emit)
    2. Alternatively, emit to command queue: /recheck-policy
  Post-action state: POLICY_EVALUATING
  Idempotent: Yes — Policy Bot re-evaluating an already-evaluated PR is harmless
```

### RETRIGGER_SOD_CHECK
```
  Precondition: Policy failed specifically on SOD validation
  Action:
    1. Emit to command queue: /recheck-sod
    2. Car bridge routes to SOD validator
  Post-action state: POLICY_EVALUATING
  Idempotent: Yes — SOD re-check is a read-only validation
```

### RETRIGGER_APPROVER_BOT
```
  Precondition: Policy passed but Approver Bot hasn't acted
  Action:
    1. Re-emit the policy pass signal that Approver Bot listens for
    2. Or emit to command queue: /recheck-approval
    3. Car bridge routes to Approver Bot
  Post-action state: Remains POLICY_PASSED (waiting for approval event)
  Idempotent: Yes — Approver Bot granting a second approval is harmless
```

### RETRIGGER_MERGE
```
  Precondition: Approved but Automerge Bot hasn't acted
  Action:
    1. Re-emit the approval signal that Automerge Bot listens for
    2. Or emit to command queue: /merge
    3. Car bridge routes to Automerge Bot
  Post-action state: MERGING
  Idempotent: Yes — merge attempt on already-merged PR returns success/no-op
```

### CLOSE_AND_REOPEN
```
  Precondition: Merge conflicts that can't be resolved by branch update
  Action:
    1. Guard: check if another open PR already exists for the same vulnerability_id
       IF yes: take NO_ACTION, log "duplicate PR exists", skip
    2. Close the current PR with a comment:
       "Closing due to merge conflicts. A new PR will be created automatically."
    3. Current PR state → CLOSED, enters TTL cleanup
    4. Delegate to CodeGenie's existing PR creation logic to create a fresh PR
       for the same vulnerability from a clean branch
    5. New PR gets a new State Table record with:
       - Fresh retry_counts (all zeros)
       - Event linking back to the old PR number for traceability
  Post-action state: Old PR → CLOSED; New PR → CREATED
  Idempotent: Partially — the duplicate guard prevents creating multiple new PRs
```

### ESCALATION (NEEDS_INTERVENTION)
```
  Precondition: Retry budget exhausted or unrecognized failure
  Action:
    1. Transition PR state to NEEDS_INTERVENTION
    2. Send notification with:
       - PR link
       - Repository
       - Vulnerability details
       - Full event history summary
       - All remediation actions attempted and their outcomes
    3. No further automated action until human resolves
  Post-action: Human reviews and either fixes + transitions state,
               or manually closes the PR
```

---

## 11. Command Queue

A command queue allows humans and the Admin API to trigger specific remediation actions on demand, decoupled from the reconciler's schedule.

### Command Flow

```
Command Sources:
  1. PR Comment — a user comments on the PR with a slash command
  2. Admin API — an API call targeting a specific PR and action

  Both sources emit a command message to the command queue.

Command Message Format:
  pr_number        — which PR to act on
  repo             — repository
  command          — the action requested (see below)
  source           — "pr-comment" or "admin-api"
  requested_by     — who issued the command (GitHub user or API caller)
  timestamp        — when the command was issued

Supported Commands:
  /rebuild             — retrigger Jenkins build
  /recheck-policy      — retrigger Policy Bot evaluation
  /recheck-sod         — retrigger SOD validation specifically
  /recheck-approval    — retrigger Approver Bot
  /merge               — retrigger Automerge Bot
  /update-branch       — merge base into head
  /close-and-reopen    — close current PR, create fresh one
  /cancel              — close the PR and mark as intentionally abandoned

Command Processing (Car Bridge):
  1. Command message arrives on the queue
  2. Car Bridge reads the command
  3. Car Bridge validates:
     - Is the PR still open?
     - Is the command valid for the PR's current state?
       (e.g., /merge doesn't make sense if checks haven't passed)
     - Does the requester have permission? (for Admin API calls)
  4. If valid, Car Bridge routes the command:
     - /rebuild          → triggers Jenkins rebuild
     - /recheck-policy   → emits event that triggers Policy Bot
     - /recheck-sod      → emits event that triggers SOD validator
     - /recheck-approval → emits event that triggers Approver Bot
     - /merge            → emits event that triggers Automerge Bot
     - /update-branch    → calls GitHub API to update branch
     - /close-and-reopen → executes close + delegates PR creation to CodeGenie
     - /cancel           → closes PR, sets state to CLOSED
  5. Car Bridge logs a COMMAND_RECEIVED event to the Events Table
  6. The resulting action flows through normal event processing
     (e.g., rebuild triggers checks, check results come back as
      webhook events, event processor updates state table)
```

### Admin API

```
The Admin API is an endpoint within CodeGenie that provides a programmatic
interface to the command queue. It does NOT execute actions directly —
it only emits command messages to the queue.

Endpoints:
  POST /api/pr/{repo}/{pr_number}/command
    Body: { "command": "/rebuild" }
    Auth: API key or service account with appropriate permissions

  GET /api/pr/{repo}/{pr_number}/status
    Returns: current state, event history, retry counts
    Purpose: inspect a PR's state without going to GitHub

  GET /api/prs/stale
    Returns: all PRs currently considered stale by the state table
    Purpose: dashboard / monitoring view

  POST /api/reconciler/run
    Triggers an on-demand reconciler run (outside of scheduler)
    Purpose: manual trigger after an outage or for testing

  POST /api/circuit-breaker/reset
    Resets the circuit breaker to CLOSED
    Purpose: manual recovery after a systemic issue is resolved

Why this architecture:
  - Admin API emits to queue → Car Bridge routes → bot executes
  - Same path whether triggered by human comment, Admin API, or reconciler
  - Single routing layer (Car Bridge) means one place to update when
    bot interfaces change
  - Queue provides backpressure and decoupling — Admin API can batch-emit
    commands for 100 PRs without overwhelming any single bot
```

---

## 12. Car Bridge Routing

The Car Bridge is the central message router. It receives events and commands from multiple sources and routes them to the appropriate handler.

```
INBOUND SOURCES:
  ┌─────────────────────┐
  │ GitHub Webhooks      │ ── PR events, check events, review events, comments
  │ Command Queue        │ ── slash commands from PR comments or Admin API
  │ Bot Status Updates   │ ── Policy Bot results, Approver Bot results, etc.
  └─────────────────────┘
            │
            ▼
      ┌───────────┐
      │ Car Bridge │
      └───────────┘
            │
            ├── GitHub webhook events ──→ Event Processor ──→ State Table + Events Table
            │
            ├── PR comment with /command ──→ Command Queue ──→ (loops back to Car Bridge)
            │
            ├── Command: /rebuild ──→ Jenkins API (trigger build)
            │
            ├── Command: /recheck-policy ──→ Policy Bot (trigger evaluation)
            │
            ├── Command: /recheck-sod ──→ SOD Validator (trigger check)
            │
            ├── Command: /recheck-approval ──→ Approver Bot (trigger approval flow)
            │
            ├── Command: /merge ──→ Automerge Bot (trigger merge)
            │
            ├── Command: /update-branch ──→ GitHub API (merge base into head)
            │
            ├── Command: /close-and-reopen ──→ GitHub API (close) + CodeGenie (create new PR)
            │
            └── Command: /cancel ──→ GitHub API (close PR)

ROUTING RULES:
  The Car Bridge decides where to send based on:
    1. Message type (webhook event vs command)
    2. For webhooks: event type determines the destination
    3. For commands: command string determines the destination
    4. Validation happens before routing (invalid commands are rejected and logged)
```

---

## 13. Event Processing Flow

How incoming events flow through the system and update state.

```
EVENT ARRIVES (from Car Bridge):

  STEP 1 — Parse and identify
    Extract: event_type, pr_number, repo, relevant details

  STEP 2 — Lookup PR in State Table
    IF PR not found:
      IF event is PR_OPENED:
        Create new State Table record (initial state: CREATED)
        Create Events Table record
        DONE
      ELSE:
        Ignore (late event for cleaned-up PR, or event for non-CodeGenie PR)
        DONE

    IF PR found AND current_state is MERGED or CLOSED:
      Ignore (late event, record awaiting TTL cleanup)
      DONE

  STEP 3 — Validate state transition
    Determine the new state implied by this event
    Check if the transition from current_state → new_state is valid
    IF invalid:
      Log anomaly: "Invalid transition for PR #{n}: {current} → {new} via {event}"
      Write event to Events Table anyway (for debugging)
      Do NOT update State Table current_state
      DONE

  STEP 4 — Update State Table
    Set current_state = new_state
    Set last_event_timestamp = now
    IF new state represents a progression (e.g., CHECKS_FAILED → CHECKS_RUNNING
       after a rebuild):
      Reset retry_counts for strategies relevant to the previous state
    IF new state is terminal (MERGED or CLOSED):
      Set ttl = now + 24 hours

  STEP 5 — Append to Events Table
    Insert new event record with all details

  STEP 6 — Deduplication
    Use event delivery ID or composite key (pr_number + event_type + timestamp)
    to detect and skip duplicate deliveries
```

---

## 14. Retry Count Reset Rules

When retry counts reset vs. persist.

```
RESET RULES:
  Retry counts for a given strategy reset when the PR naturally progresses
  PAST the state that strategy addresses.

  Examples:
    - PR was in CHECKS_FAILED, reconciler triggered rebuild (rebuild count = 1)
    - Rebuild succeeds, PR moves to CHECKS_PASSED
    - rebuild count resets to 0
    - If PR later fails checks again (due to new commits from branch update),
      rebuild count starts fresh at 0

    - PR was in POLICY_PASSED, reconciler retriggered Approver Bot (retrigger count = 1)
    - Approver Bot responds, PR moves to APPROVED
    - retrigger_approver_bot count resets to 0

  DO NOT RESET:
    - If the reconciler retries and the PR stays in the same state
      (e.g., rebuild triggered but checks fail again → count increments, not resets)
    - close_and_reopen count NEVER resets on the same PR
      (it's tracked per vulnerability across PR replacements if needed)

RESET MAPPING:
  Strategy                  Resets when PR reaches
  ────────                  ──────────────────────
  rebuild                   CHECKS_PASSED
  branch_update             CHECKS_RUNNING (checks restarted after update)
  retrigger_policy_bot      POLICY_PASSED or POLICY_FAILED (bot responded)
  retrigger_approver_bot    APPROVED (approval received)
  retrigger_automerge_bot   MERGING or MERGED (merge attempted/succeeded)
  retrigger_sod_check       POLICY_PASSED or POLICY_FAILED (re-evaluation complete)
  close_and_reopen          Never resets (1 attempt max, then escalate)
```

---

## 15. Circuit Breaker Logic

Prevents the reconciler from flooding the system during widespread outages.

```
STATE: CLOSED (normal operation)
  All remediation actions are allowed.
  Track: success and failure counts per sliding window (e.g., 15 minutes)

TRIP CONDITION:
  IF (failures in window / total actions in window) > failure_threshold (e.g., 50%)
  AND total actions in window > minimum_sample_size (e.g., 5)
  THEN: transition to OPEN

STATE: OPEN (remediation paused)
  No remediation actions are dispatched.
  Reconciler still runs and logs stale PRs (for visibility) but takes no action.
  Notification sent: "Circuit breaker tripped — {failure_rate}% failure rate"
  Start cooldown timer (e.g., 10 minutes)

STATE: HALF-OPEN (probing)
  After cooldown elapses, allow exactly ONE remediation action through.
  IF it succeeds: transition back to CLOSED
  IF it fails: transition back to OPEN, reset cooldown timer

MANUAL OVERRIDE:
  Admin API endpoint to force circuit breaker to CLOSED
  (for when a human confirms the underlying issue is resolved)
```

---

## 16. End-to-End Happy Path

Everything works, no remediation needed:

```
1. CodeGenie creates PR for vulnerability
   → Event: PR_OPENED
   → State Table: new record, state = CREATED

2. GitHub triggers CI checks
   → Event: CHECKS_STARTED
   → State: CHECKS_RUNNING

3. Jenkins build passes, all checks green
   → Event: CHECKS_PASSED
   → State: CHECKS_PASSED

4. Policy Bot evaluates: SOD ✓, build ✓, branch protections ✓
   → Event: POLICY_PASSED
   → State: POLICY_PASSED

5. Approver Bot sees Policy Bot approval, issues approval review
   → Event: APPROVAL_GRANTED
   → State: APPROVED

6. Automerge Bot sees approval + all checks green, merges
   → Event: MERGE_SUCCEEDED
   → State: MERGED, ttl set

7. DynamoDB TTL deletes record after 24 hours
```

---

## 17. End-to-End Self-Healing Path (Example: Transient CI Failure)

```
1. CodeGenie creates PR
   → State: CREATED → CHECKS_RUNNING

2. Jenkins build times out (infra issue)
   → Event: CHECKS_FAILED (payload: "timeout")
   → State: CHECKS_FAILED, substatus = TRANSIENT

3. 30 minutes pass, no change. Reconciler runs.
   → Reconciler queries: CHECKS_FAILED + last_event > 30 min ago
   → Reconciler polls GitHub: confirms checks failed, no conflicts, branch up to date
   → Classifier: CHECKS_FAILED + transient signal → RETRY_CHECKS
   → Retry budget: rebuild count = 0, max = 3. Budget OK.
   → Strategy: trigger Jenkins rebuild
   → Event: REMEDIATION_REBUILD logged
   → State: CHECKS_RUNNING, retry_counts.rebuild = 1

4. Jenkins build passes this time
   → Event: CHECKS_PASSED
   → State: CHECKS_PASSED, retry_counts.rebuild resets to 0

5. Normal flow resumes: Policy Bot → Approver Bot → Automerge Bot → Merged
```

---

## 18. End-to-End Command Queue Path (Example: User Triggers Rebuild)

```
1. PR is stuck in CHECKS_FAILED.
   Developer notices before reconciler acts.

2. Developer comments on PR: "/rebuild"

3. GitHub sends issue_comment webhook to Car Bridge

4. Car Bridge detects slash command pattern in comment body
   → Emits command message to Command Queue:
     { pr_number: 42, repo: "my-app", command: "/rebuild",
       source: "pr-comment", requested_by: "danny" }

5. Car Bridge picks up command from queue
   → Validates: PR #42 is open, current state allows rebuild
   → Routes: triggers Jenkins rebuild via Jenkins API
   → Logs: COMMAND_RECEIVED event to Events Table

6. Jenkins build runs and passes
   → Normal webhook flow: CHECKS_PASSED event → State Table updated

7. PR continues through normal pipeline
```

---

## 19. End-to-End Admin API Path (Example: Batch Rebuild After Outage)

```
1. Jenkins had a 2-hour outage. 15 CodeGenie PRs failed with timeouts.
   Circuit breaker tripped during the outage.

2. Jenkins is back. Engineer resets circuit breaker:
   POST /api/circuit-breaker/reset

3. Engineer queries stale PRs:
   GET /api/prs/stale
   → Returns 15 PRs in CHECKS_FAILED state

4. Engineer triggers batch rebuild:
   For each PR:
     POST /api/pr/{repo}/{pr_number}/command
     Body: { "command": "/rebuild" }

5. Each command hits the Command Queue
   → Car Bridge processes them sequentially (queue provides backpressure)
   → Jenkins rebuilds fire one at a time (or with controlled concurrency)

6. Results flow back through normal event processing
   → PRs that pass move through the pipeline
   → PRs that fail again will be caught by the next reconciler run
```
