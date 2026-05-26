# Delivery Guide — Agentic Governance Blueprint for Fabric

> **Audience:** facilitators, coaches, customer-engagement leads, and event
> organizers who are running this blueprint as a workshop, hackathon, or guided
> customer engagement.
>
> **Participant-facing instructions live in
> [`challenges/`](../challenges/).** This document is everything *around* the
> challenges: timings, pre-flight, coaching, judging, and how to evolve the
> blueprint after each delivery.

---

## 1. What this blueprint is (and isn't)

The **Agentic Governance Blueprint for Fabric** is an agent-assisted governance
framework: a set of repeatable templates, checks, and guided exercises that
takes a team from an empty Fabric tenant to a fully governed, PR-driven control
plane. It is designed to be delivered repeatedly to different customers and to
**learn from every delivery**.

- ✅ Use it as: a 1-day immersion, a 2-day hackathon, a multi-week customer
  engagement, or self-paced enablement.
- ✅ Use it to: codify a customer's standards, generate their first auditable
  artifacts, and seed a long-lived governance repo they own.
- ❌ Don't use it as: a CTF. Solutions are linked from each challenge; coaching
  the *why* matters more than withholding the *how*.

## 2. Delivery formats

Pick the format that matches the customer's appetite and seniority. Every
format reuses the same `challenges/` content; only scope and timing change.

| Format | Duration | Audience | Coverage | Notes |
|---|---|---|---|---|
| **Express demo** | 90 min | Execs, architects | Walk through 00 + 01 already-provisioned | No hands-on; live narration of an existing PR + run |
| **1-day immersion** | 6–7 hrs | Platform + data engineers | 00 → 01 → pick **two** of 02-08 | Skip Capstone; finish with a guided demo |
| **2-day hackathon** | 12–14 hrs | Mixed teams of 3–5 | 00 → 01 → 4-5 of 02-08 → Capstone | Default format; judging + prizes optional |
| **Multi-week engagement** | 4–8 weeks | Customer platform team | All 10, in real tenant, real workloads | Coach attends weekly working sessions; ends with a customer-owned fork |
| **Self-paced enablement** | rolling | Individuals | Any subset | Read-only solutions, async coach Q&A |

> **Rule of thumb:** every team needs Challenge 00 done **before** the clock
> starts on the actual workshop. Don't burn workshop time on tenant + identity
> setup unless that's the *only* learning objective.

## 3. Pre-event checklist (organizer / coach)

Run this **2 weeks before** delivery. The further you can push setup to before
the event, the more learning happens during the event.

### 3.1 Tenant + identity

- [ ] Fabric tenant identified, capacity provisioned (F2+; **F4+** if you plan to
      run Challenges 05 or 07).
- [ ] One SPN per team **or** one shared SPN with per-team federated credentials
      created. Use the layout in [`docs/identity-model.md`](identity-model.md).
- [ ] Tenant settings toggled per [`docs/setup.md`](setup.md). Allow ≥ 15 min
      for propagation before you smoke-test.
- [ ] SPN granted **Fabric Administrator** and **Capacity Admin** roles.
- [ ] Sensitivity labels (Public/General/Confidential/Highly Confidential)
      exist in Purview and are scoped to the SPN's publishing group.

### 3.2 GitHub

- [ ] Org for the event chosen; each team will fork into it (or get a
      pre-created repo with branch protection already configured).
- [ ] Repo variables present: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`,
      `FABRIC_CAPACITY_ID`, `DEFAULT_OWNER_UPN`, `LIVE_CHECKS`.
- [ ] `production` environment created with required reviewer.
- [ ] Branch protection on `main`: required PR review, required `validate`
      status check, CODEOWNERS review, restrict pushes to GitHub Actions.

### 3.3 Per-participant prerequisites

Send participants **one week ahead**:

- [ ] Microsoft Entra ID account in the event tenant (or guest invite).
- [ ] VS Code + GitHub Copilot extension **or** GitHub Copilot CLI installed.
- [ ] Python 3.12+, Git, Azure CLI installed locally.
- [ ] Fabric Core MCP and Fabric local MCP installed and authenticated
      (see [`docs/mcp-and-skills.md`](mcp-and-skills.md)).
- [ ] At least one Skill for Fabric installed (e.g., `spark-authoring-cli`).
- [ ] Smoke-test prompts from Challenge 00 § Task 8 all return useful answers.

### 3.4 Coaching capacity

| Cohort size | Recommended coaches |
|---|---|
| 1 team (3–5 people) | 1 coach |
| 2–3 teams | 1 coach + 1 floater |
| 4–6 teams | 2 coaches + 1 floater |
| 7+ teams | 1 coach per 3 teams + 1 lead facilitator |

Coaches should have completed Challenges 00, 01, and the challenges they will
shepherd at least once.

### 3.5 Materials to have on hand

- [ ] Latest copy of [`docs/troubleshooting.md`](troubleshooting.md) open in a tab.
- [ ] [`docs/glossary.md`](glossary.md) printed or open for newcomers.
- [ ] Shared chat channel for the event (Teams / Slack / Discord).
- [ ] Feedback form link (see § 8).
- [ ] Optional: prize / certificate template for the Capstone winners.

## 4. Sample agendas

Agendas assume Challenge 00 is **complete** before day 1.

### 4.1 One-day immersion (6.5 hrs of content + breaks)

| Time | Block | Notes |
|---|---|---|
| 09:00 | Kickoff + Blueprint overview | 15 min slides, 15 min repo walkthrough |
| 09:30 | Challenge 01 — Workspace as code | Everyone does this |
| 11:30 | Break | |
| 11:45 | Pick one of: 02 / 04 / 03 | Coach assigns based on customer pain |
| 13:00 | Lunch | |
| 14:00 | Pick one of: 05 / 06 / 08 | Heavier hands-on |
| 16:30 | Show & tell (10 min/team) | No formal judging |
| 17:00 | Retro + feedback form | |

### 4.2 Two-day hackathon (default)

**Day 1**

| Time | Block |
|---|---|
| 09:00 | Kickoff, team formation, blueprint overview |
| 09:30 | Challenge 01 (all teams) |
| 11:30 | Break |
| 11:45 | Challenge 02 OR 03 OR 04 (team choice) |
| 13:00 | Lunch |
| 14:00 | Challenge 05 OR 06 (team choice) |
| 16:00 | Break |
| 16:15 | Stretch goal sprint OR start Capstone planning |
| 17:00 | Day 1 retro |

**Day 2**

| Time | Block |
|---|---|
| 09:00 | Standup — what's blocking each team |
| 09:30 | Challenge 07 OR 08 (team choice) |
| 12:00 | Lunch |
| 13:00 | Capstone build |
| 16:00 | Demos (10 min/team, see § 6) |
| 17:00 | Judging + awards + retro + feedback form |

### 4.3 Multi-week customer engagement

| Week | Focus |
|---|---|
| 0 | Pre-flight (§ 3); kickoff call |
| 1 | Challenges 00 + 01 in customer tenant |
| 2 | Challenge 02 (items) + Challenge 03 (domains/capacities) |
| 3 | Challenge 04 (RBAC) |
| 4 | Challenge 05 (medallion) on a real customer use-case |
| 5 | Challenge 06 (data agent) |
| 6 | Challenge 07 (audit + observability) |
| 7 | Challenge 08 (promotion pipelines) |
| 8 | Capstone — production cutover of one real workload; retro; handover |

## 5. Per-challenge facilitator cards

Each card answers: how hard, how long, what it depends on, what to watch out
for, and what "done" looks like.

> Durations are **median wall-clock** assuming 2–3 motivated engineers with
> Challenge 00 complete. Halve for solo experts, double for first-timers.

### Challenge 00 — Setup
- **Difficulty:** Medium · **Duration:** 90–120 min · **Dependencies:** none
- **Coach watch-outs:**
  - Federated-credential subject typos cause `AADSTS70021`; subject is
    case-sensitive (see [`docs/troubleshooting.md`](troubleshooting.md) § OIDC).
  - Tenant settings take **up to 15 min** to propagate; participants will
    re-run and assume they broke things.
  - Microsoft Graph MCP is *optional* but unlocks Challenge 04 UPN → objectId
    resolution — install it now to save context-switching later.
- **Done when:** all four smoke-test prompts in § Task 8 return useful answers.

### Challenge 01 — Workspace as code
- **Difficulty:** Foundational · **Duration:** 90–120 min · **Dependencies:** 00
- **Coach watch-outs:**
  - The deliberate-failure task (§ Task 2) is the most important learning
    moment — don't let teams skip it.
  - Drift detection requires participants to make an out-of-band change in the
    portal; some will be reluctant to "break" things. Encourage it.
  - The `managed-by:` marker is what enables drift to distinguish managed vs
    unmanaged — point it out explicitly in the workspace description.
- **Done when:** one PR-created workspace exists, drift cycle exercised end-to-end.

### Challenge 02 — Items as code
- **Difficulty:** Medium · **Duration:** 120–180 min · **Dependencies:** 00, 01
- **Coach watch-outs:**
  - Item kinds have different naming regexes; participants often start with one
    and forget to parameterize.
  - The local MCP `docs_item-definitions` tool is the fast path to correct
    payloads — many teams reinvent the schema from web search.
  - Skills generate code; **manifest stays the source of truth**. Watch for
    teams treating Skill output as authoritative.
- **Done when:** ≥ 1 lakehouse + 1 notebook + 1 warehouse exist via PR; missing
  description blocks a PR.

### Challenge 03 — Domains, capacities, sensitivity
- **Difficulty:** Medium · **Duration:** 120–180 min · **Dependencies:** 00, 01
- **Coach watch-outs:**
  - Requires SPN to be **Fabric Administrator** (admin APIs) and member of the
    Purview MIP scope (label apply). Verify before starting.
  - Label-promotion CODEOWNERS rule is easy to mis-scope — review the path
    glob with the team.
  - Sensitivity-label apply via the Power BI admin API is the most likely
    permission failure mode.
- **Done when:** prd-* workspace on a dev-only capacity fails validation; portal
  label removal opens a drift issue.

### Challenge 04 — Access & RBAC lifecycle
- **Difficulty:** Medium · **Duration:** 120–180 min · **Dependencies:** 00, 01
- **Coach watch-outs:**
  - Group-first vs User-by-exception is the whole challenge. If teams default
    to User principals, redirect early.
  - JIT break-glass is a stretch concept — make sure they understand the
    auto-expiry follow-up PR before they leave.
  - Microsoft Graph MCP makes UPN → objectId resolution painless; without it
    teams paste raw GUIDs and lose 30 min hunting for the right one.
- **Done when:** a `User Admin on prd-*` PR is blocked; quarterly review
  workflow opens a PR against an expiring binding.

### Challenge 05 — Medallion bootstrap
- **Difficulty:** Medium-High · **Duration:** 180–240 min · **Dependencies:** 00, 01, 02
- **Coach watch-outs:**
  - F4+ capacity strongly recommended; F2 causes Spark queueing.
  - The `e2e-medallion-architecture` skill is composable — teams panic at the
    full Bronze/Silver/Gold; remind them they can scope to two tiers.
  - Capturing Skill output back into `items/` (`capture_medallion_output.py`)
    is what makes drift work later. Don't skip.
- **Done when:** one medallion manifest produces ≥ 3 workspaces, ≥ 3
  lakehouses, ≥ 1 certified semantic model.

### Challenge 06 — Fabric Data Agent governance
- **Difficulty:** High · **Duration:** 180–240 min · **Dependencies:** 00, 01, 02, 03, 04
- **Coach watch-outs:**
  - This challenge has the **strictest prereq chain** — confirm 04 is done.
  - RAI lint is opinionated; tailor `rules/agent/banned_phrases.yaml` to the
    customer's policy *before* the event.
  - Requires Fabric Data Agent feature enabled on the capacity; check ahead.
  - Purview DSPM stretch goal requires Purview integration set up — flag as
    advanced.
- **Done when:** one agent answers an example question with Confidential gold
  data; an unmanaged data source PR is blocked.

### Challenge 07 — Audit & observability
- **Difficulty:** High (densest Skills usage) · **Duration:** 240–300 min · **Dependencies:** 00, 01, 02
- **Coach watch-outs:**
  - Four authoring skills + one consumption skill in one challenge — pace
    accordingly. Some teams will only finish Eventhouse + dashboard.
  - GitHub webhook configuration is often blocked by org policy; have a
    fallback (admin-API export option in § Task 4).
  - Activator reflexes can spam channels — set test thresholds high, then
    tighten after smoke test.
- **Done when:** PR events appear in `pr_events` within 60 s; one Activator
  reflex has fired.

### Challenge 08 — Deployment pipelines
- **Difficulty:** Medium-High · **Duration:** 180–240 min · **Dependencies:** 00, 01, 02
- **Coach watch-outs:**
  - Requires dev/stg/prd workspace trio under management before promotion
    works — many teams arrive with only dev.
  - Rollback flow (`revert/prd`) is a stretch for most teams; demo it rather
    than have everyone implement.
  - PR-label triggers are subtle; participants often forget the
    `pull_request: types: [labeled]` event.
- **Done when:** `promote/stg` label promotes items dev → stg; `promote/prd`
  triggers the production environment gate.

### Capstone — End-to-end integration
- **Difficulty:** Integration · **Duration:** 240–360 min · **Dependencies:** any 5+
- **Coach watch-outs:**
  - Scope creep is the killer. Push teams to pick **5 challenges** and stop.
  - The judging rubric ([`challenges/capstone/challenge.md`](../challenges/capstone/challenge.md))
    is the source of truth — use it as the demo checklist too.
  - The 10-minute demo is a hard limit. Practice ahead.
- **Done when:** a single PR (or short stacked series) exercises the team's
  chosen challenges and all rubric criteria can be demoed live.

## 6. Demo logistics (hackathon format)

Allocate **10 minutes per team**: 7 min demo + 3 min Q&A. Judges score against
the Capstone rubric in real time.

**Required demo content** (every team):

1. The original PR open in GitHub.
2. The sticky validate comment (passing).
3. The provision run with environment approval timestamp.
4. The Fabric portal showing the live resources.
5. The governance dashboard filtered to this team's pipeline.
6. (If they did Challenge 06) the agent answering a sample question.
7. (Optional) an injected drift event with the detector catching it.

**Stage management tips:**

- Pre-share screens; don't waste demo minutes hunting for windows.
- Coach the closer to read the rubric out loud as they hit each item.
- Time-box hard. If the buzzer goes, the next team starts.

## 7. Coaching playbook

Five principles that apply across every challenge:

1. **Coach the *why*, not the *how*.** Solutions are linked. The goal is for
   teams to understand the trade-off (e.g., "why CODEOWNERS *and* environment
   gate?"), not to type faster.
2. **Push teams to the agent first.** If a team is stuck writing a payload,
   ask "did you try the local MCP `docs_*` tool for that item kind?" before
   handing them the answer.
3. **Encourage the deliberate-failure task in every challenge.** Watching a
   policy block a bad PR is more memorable than watching a good PR pass.
4. **Surface the audit trail.** Every action a team takes should leave a
   trace: PR, sticky comment, workflow run, marker. Point at the trail
   constantly.
5. **Time-box stretch goals.** Stretch goals are bait for fast teams. If a
   team is behind on the main task, redirect away from stretch.

**De-escalation patterns:**

| Symptom | First thing to try |
|---|---|
| `401` from Fabric Core MCP | Re-add MCP server in VS Code; re-auth. |
| `AADSTS70021` | Verify federated credential subject string exactly matches. |
| 403 from Fabric REST in workflow | Wait 15 min for tenant settings; verify SPN is in capacity admins. |
| `429 Too Many Requests` | The retry in `scripts/_fabric.py` is already handling it; wait. |
| "Skill not available" | Confirm both MCP servers + the Skill are installed; restart agent. |
| Drift detector silent | Check the `managed-by:` marker is in the workspace description. |

Full catalog in [`docs/troubleshooting.md`](troubleshooting.md).

## 8. Post-delivery — feedback and iteration

The blueprint is intended to **improve after every delivery**. Each event is a
source of new requirements, sharper challenges, and customer-specific
adaptations. Funnel that signal back into the repo via PRs.

### 8.1 Collect feedback

At the end of every delivery, capture:

- Per-challenge: difficulty rating (1–5), time taken, what blocked them.
- Cross-cutting: best moment, worst moment, what was missing.
- Net-new asks: scenarios the customer hit that no challenge covers.
- Bugs in the blueprint itself (broken links, stale screenshots, policy gaps).

Use a single feedback form (Forms / Google Forms / GitHub Discussions —
whatever the org standard is) and link it from the closing slide.

### 8.2 Triage feedback into the inbox

Within **5 business days** of the event, the lead facilitator opens a single
**delivery retro PR** that:

1. Adds a `deliveries/<yyyy-mm-dd>-<customer-or-event>.md` file capturing:
   - Format used and headcount.
   - Which challenges were attempted / completed.
   - Aggregated ratings and quotes.
   - The triaged feedback items (see § 8.3).
2. References each net-new item as a GitHub issue (one per actionable
   feedback item) so they can be tracked independently.

### 8.3 Turn feedback into challenges (or challenge changes)

Feedback maps to one of four PR types. Use the type as the PR title prefix.

| Prefix | Meaning | Examples |
|---|---|---|
| `fix:` | Bug or doc rot in an existing challenge | Broken link in 03; outdated screenshot in 07 |
| `enhance:` | Sharpen an existing challenge | Add a new policy rule to 01; clearer success criteria in 04 |
| `adapt:` | Customer-specific variant kept alongside the original | A "regulated insurance" variant of 06 that adds Purview DSPM gating |
| `feat:` | Brand-new challenge | A "Data Mesh federated governance" challenge for tenants using multiple domains |

> **Every PR that adds or changes challenge content must keep the contract
> defined in [`README.md`](../README.md) § "Contributing back":** each
> challenge demonstrates ≥ 1 MCP server **and** ≥ 1 Skill, and policy / schema
> changes need CODEOWNERS review.

### 8.4 New-challenge checklist

If a customer's ask graduates to a `feat:` PR, the new challenge folder
(`challenges/<NN>-<slug>/`) must include:

- [ ] `challenge.md` following the existing template — Outcome, Why, Learning
      objectives, Prerequisites, Tasks, Success criteria, Stretch goals,
      MCP tips, Skills tips, References.
- [ ] Difficulty + duration estimate added to § 5 of this guide.
- [ ] Dependency listed in § 5 of this guide and in the README learning-path
      diagram if it's a first-class node.
- [ ] At least one MCP tool reference and one Skill reference.
- [ ] At least one deliberate-failure task (a PR that should be blocked).
- [ ] A `solution/` reference implementation (or a link to one in a private
      branch if the customer asked for confidentiality).
- [ ] Troubleshooting entries added to [`docs/troubleshooting.md`](troubleshooting.md)
      for the new failure modes you anticipate.
- [ ] An entry in `deliveries/<yyyy-mm-dd>-*.md` documenting which customer
      delivery sourced the challenge.

### 8.5 Adapted-challenge checklist

`adapt:` PRs sit **alongside** the original (don't overwrite it). Layout:

```
challenges/
  06-data-agent-governance/
    challenge.md                       ← canonical
    variants/
      insurance-regulated/
        challenge.md                   ← adapted; references canonical for shared bits
        rules-overlay.yaml             ← additional policy on top of rules/policy.yaml
```

A variant must:

- [ ] Open with a one-paragraph "When to use this variant" framing.
- [ ] Reference the canonical challenge for setup, prereqs, and shared tasks.
- [ ] List only the *delta* tasks, success criteria, and rules.
- [ ] Be tagged in the front-matter (or first heading) with the customer or
      industry it was sourced from, e.g. `variant: insurance-regulated`.

### 8.6 Cadence

| Cadence | Action |
|---|---|
| **After every delivery** | Retro PR with `deliveries/<date>-*.md` + issues |
| **Monthly** | Lead facilitator triages open feedback issues into `fix` / `enhance` / `adapt` / `feat` PRs |
| **Quarterly** | Review § 5 durations + difficulty ratings against the latest deliveries and update |
| **Annually** | Re-evaluate the learning-path graph in the README — are 10 challenges still the right shape? |

## 9. Suggested feedback questions

Drop these into your feedback form verbatim if useful:

1. Which challenges did you attempt? Which did you complete?
2. Rate each attempted challenge 1–5 on difficulty, 1–5 on clarity, 1–5 on
   business relevance.
3. How long did each challenge take? (in 30-minute buckets)
4. What was the single most useful idea you're taking back to your team?
5. What did you *want* the blueprint to cover that it didn't?
6. Where did the agent (MCP / Skills / Copilot) save you the most time? Where
   did it get in your way?
7. If you had one PR's worth of time to improve the blueprint, what would
   you change?

## 10. References

- [`README.md`](../README.md) — project front door and learning-path diagram
- [`docs/setup.md`](setup.md) — one-time operator runbook
- [`docs/identity-model.md`](identity-model.md) — OIDC, federated credentials, SPN scopes
- [`docs/mcp-and-skills.md`](mcp-and-skills.md) — Fabric MCP + Skills install and usage
- [`docs/workspace-approval-workflow.md`](workspace-approval-workflow.md) — Challenge 01 design reference
- [`docs/troubleshooting.md`](troubleshooting.md) — shared error catalog
- [`docs/glossary.md`](glossary.md) — Fabric + governance terminology
- [`challenges/`](../challenges/) — the 10 participant-facing challenges
