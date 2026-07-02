# CS Playbooks: Agent Pattern Matching Library

## Overview

These playbooks encode the pattern matching judgment of high-performing CSMs into a structured form an AI agent can act on. The agent's job is not to replace CSM judgment but to mimic how a great CSM operates: catch a single signal, pull threads across every available data source, and either form a hypothesis worth surfacing or hold the observation until the picture clarifies.

The playbooks are pattern definitions. The investigation logic that supports them is shared across all three.

## Shared Operating Model

**Single signal activates the agent.** A CSM doesn't wait for combinations to form before they get curious. Any single signal — internal or external — wakes the agent and sends it looking.

**The agent investigates correlating signals.** Once activated, the agent pulls evidence across all relevant dimensions: usage, users, activity, support, relationship, communication, and external context.

**Three possible outputs:**

1. **Hypothesis** — Correlating signals match a defined pattern. Surface to the CSM with context.
2. **Recheck scheduled** — Initial investigation inconclusive. Agent will look again at the appropriate interval.
3. **Monitor / health signal** — Recheck also inconclusive. The signal still happened and is surfaced as a low-priority observation rather than dismissed.

**Cross-playbook routing.** When multiple playbooks match the same account simultaneously, the agent routes to a combined alert for human investigation rather than firing standalone hypotheses. The combined alert is a qualitatively different output that signals to the CSM that the situation is ambiguous and needs their judgment.

**Mutual exclusion: Hard Churn and Silent Churn.** These two playbooks cannot fire on the same account at the same time by construction. Silent Churn requires absence of activity and is disqualified by red sentiment. Hard Churn requires presence of distress signals and treats red sentiment as a corroborator.

**The agent surfaces signals. The CSM brings relationship judgment.** The playbooks do not gate on relationship state. If the signals match the pattern, the hypothesis fires. The CSM decides how to engage based on context the agent does not have.

---

# Playbook 1: Expansion Ready

## 1. Objective

Identify accounts where customer behavior, business context, and engagement patterns suggest they are positioned to grow with the product. Surface a hypothesis specific enough that the CSM can act on it without redoing the pattern matching.

The goal is not to flag healthy accounts. It is to flag accounts where there is a defensible reason to believe the next conversation should be about doing more.

## 2. Trigger Criteria

Any single signal activates the agent. The agent investigates correlating signals before forming a hypothesis.

### Activating signals (any one wakes the agent)

**Internal:**

- Sustained usage above contracted baseline on any product (30+ days, utilization_rate > 1.15)
- New usage detected on uncontracted or previously dormant product
- Increase in active users on the platform
- Sustained increase in page views or login activity (14+ days)
- Informational support tickets with quick resolution and positive sentiment
- Champion or executive sponsor initiating outbound contact
- Director or VP level contact engaging (CRM integration required)
- Cross-functional engagement: new contacts from product, security, or software developer functions

**External:**

- Funding announcement
- Acquisition (as acquirer)
- Strategic initiative or product launch announcement
- Leadership addition relevant to champion or buyer org
- Hiring surge in roles that map to product user base

**Anomalies:**

- One-day spike in usage (immediate check, recheck if inconclusive)

## 3. Risk / Why It Matters

Expansion is the output of trust, not the goal of an outreach campaign. Accounts that are genuinely expansion-ready will expand with or without intervention if the relationship is intact, but the timing, size, and shape of that expansion is heavily influenced by whether the CSM shows up at the right moment with the right framing.

Missing the signal does not mean the customer churns. It means they expand reactively, in smaller increments, often through procurement rather than partnership. That is the difference between a customer telling you what they need and a customer being shown what is possible.

Mis-firing on the signal is worse. An expansion conversation with an account that is not actually ready erodes trust, signals that the CSM is incentive-driven rather than outcome-driven, and triggers the "friend who only calls when they want something" pattern. Confidence in the hypothesis matters as much as the hypothesis itself.

## 4. Required Inputs

The agent must assemble these before producing a hypothesis:

- 90-day utilization trend per contracted product
- Current usage vs contracted baseline per product
- Detection of usage on uncontracted or adjacent products
- Feature breadth score trajectory per product
- 60-day activity log: who initiated, who was contacted, sentiment trajectory
- Champion and executive sponsor active status
- New contacts appearing in activity log within 30 days
- Title and function of recently engaged contacts (CRM integration)
- Open and recently resolved support tickets, weighted by category and sentiment
- Login activity and page view trends (14 and 30 day windows)
- Active user count trend
- Renewal date proximity
- RSS/external signals within last 90 days
- Last meaningful CSM touch and what was discussed

## 5. Execution Steps

1. Detect activating signal
2. Run signal check across all correlating signal categories: usage, users, activity, support character, contacts, external events
3. Apply pattern match logic (see Decision Tree) to determine output
4. If hypothesis fires: assemble narrative including what was observed, what it likely means, and what to confirm with the customer
5. Identify the most active stakeholder as suggested entry point for the CSM
6. Note timing context relative to renewal and any external event window
7. If recheck scheduled: queue for re-investigation at appropriate interval
8. If monitor: route to shared monitor output
9. If another playbook also matches: route to combined alert

## 6. Messaging Assets

To be developed separately.

## 7. Decision Tree

### Pattern match logic

Hypothesis fires when activating signal is corroborated by at least one strong correlating signal OR two soft correlating signals.

**Strong correlating signals:**

- New users onboarding within 30 days of activating signal
- Director or VP level contact engaging
- Cross-functional engagement (product, security, software developer titles)
- Sustained growth across multiple contracted products simultaneously
- Activity in dormant adjacent product
- Sustained page view or login increase (14+ days)

**Soft correlating signals:**

- Informational support tickets with quick resolution and positive sentiment
- Single new login from new contact
- External event corroborated by minor internal movement

### Routing rules

- Activating signal + strong correlating signal → expansion hypothesis fires
- Activating signal + two soft correlating signals → expansion hypothesis fires
- Activating signal + one soft correlating signal → recheck scheduled
- Activating signal + no correlating signals → recheck scheduled

### Recheck windows

- Internal usage anomalies and one-day spikes: 3 days
- External events (funding, strategic announcements, leadership changes): 7-10 days
- One recheck only

### Post-recheck

- Correlating signals now present → hypothesis fires
- Still inconclusive → route to monitor

### Disqualifying patterns (route away from expansion)

- Usage spike with no human signal after recheck → route to monitor as potential misconfiguration or health observation
- Sustained over-utilization on one product while adjacent contracted products remain dormant → not expansion, customer has demonstrated they do not want adjacent product

### Cross-playbook routing

- If another playbook also matches simultaneously → route to combined alert for human investigation, not standalone Expansion Ready hypothesis

## 8. Success Metrics

### Leading indicators

- Hypothesis acceptance rate by CSMs
- Meeting secured with the recommended stakeholder
- Customer confirmation of the underlying driver
- New contacts identified through validation conversation

### Lagging indicators

- Expansion opportunity created in pipeline tied to the hypothesis
- Expansion closed-won attributable to the play
- Time from signal to opportunity creation
- Average expansion deal size from agent-surfaced hypotheses vs reactive expansion

### Expected timeline

- Signal to hypothesis: same day
- Hypothesis to CSM action: within 5 business days
- CSM action to validation conversation: within 10 business days
- Validation to opportunity (if confirmed): within 30 days

---

# Playbook 2: Silent Churn Risk

## 1. Objective

Identify accounts where the customer is quietly disengaging across multiple dimensions of the relationship at the same time. Surface a hypothesis that gives the CSM the chance to re-engage before the absence becomes a non-renewal.

The goal is not to flag unhappy customers. Unhappy customers are loud — they escalate, they complain, they show up red in the activity log. Silent churn is the opposite. Everything looks fine on the surface while engagement disappears underneath.

## 2. Trigger Criteria

Any single signal activates the agent. The agent investigates correlating signals before forming a hypothesis.

### Activating signals (any one wakes the agent)

**Internal — strong activators:**

- Plateau below contracted usage (under 85% of contract for 60+ days with no upward movement)
- Slightly declining usage from a previously higher state (30+ days of drift below recent baseline)
- Abrupt drop in support ticket volume after a history of engagement (5+ tickets in prior 6 months, 0 in last 60-90 days)
- No meaningful activity in activity log for 60+ days

**Internal — standard activators:**

- Plateau at or above contracted usage (85-100%+ of contract for 60+ days with no upward movement)
- Champion marked inactive or exited
- Executive sponsor marked inactive, or no executive sponsor exists
- Communication pattern shows CSM-initiated only for 60+ days
- Declining active user count over 30-day window
- Declining login activity or page views over 30-day window

**External:**

- Layoffs announced at customer
- Customer acquired (as the acquired party)
- Public restructuring or distress signals
- Loss of leadership relevant to champion or buyer org

## 3. Risk / Why It Matters

Silent churn is the most expensive kind of churn because it's the kind that surprises everyone. By the time it surfaces — usually at renewal — the customer has already mentally moved on. There's no save motion. There's no recovery plan. There's a polite email saying the contract won't renew.

Silent churn happens because the relationship thinned without anyone noticing. The champion left and wasn't replaced. The executive sponsor stopped attending QBRs. Usage plateaued at "fine." Tickets stopped coming because the customer stopped trying. None of these things look like a crisis on their own. Together, they are.

Where a customer plateaus matters enormously. A plateau at full contract means the customer is consuming what they paid for. A plateau below contract means adoption stalled before reaching committed scope, and the renewal conversation will start with the customer questioning the contract size.

The cost of missing the signal is the renewal. The cost of mis-firing is small — a check-in conversation with a customer who is actually fine. The asymmetry favors firing the hypothesis even when the agent isn't certain.

## 4. Required Inputs

The agent must assemble these before producing a hypothesis:

- 90-day utilization trend per contracted product, expressed as percent of contracted usage
- Week-over-week and month-over-month growth rate to identify where the curve flattened
- Active user count trend over 30 and 60 day windows
- Login activity and page view trends (30 and 60 day windows)
- 60-day activity log: who initiated, who was contacted, sentiment
- Champion and executive sponsor active status
- Support ticket history over last 6 months: volume, severity, category, resolution time
- Support ticket pattern in last 60-90 days vs prior 6 months
- Last meaningful CSM touch (date and what was discussed)
- Communication ratio: CSM-initiated vs customer-initiated in last 60 days
- Customer response rate to CSM outreach in last 60 days
- Renewal date proximity
- RSS/external signals within last 90 days (especially distress-oriented)
- Sentiment trajectory in activity log (presence of red is disqualifying)

## 5. Execution Steps

1. Detect activating signal and classify as strong or standard
2. Check for red sentiment in last 60 days — if present, do not fire (this is loud churn, not silent)
3. Run signal check across all dimensions of absence: usage, users, activity, support, relationship, communication, external
4. Apply pattern match logic (see Decision Tree) to determine output
5. If hypothesis fires: assemble narrative including which dimensions have gone quiet, the timeline of the disengagement, where on the contract curve the customer plateaued, and what specifically to investigate with the customer
6. Identify the last active stakeholder (even if currently inactive) as suggested re-engagement entry point
7. Note renewal proximity as urgency context in the hypothesis output
8. If recheck scheduled: queue for re-investigation at appropriate interval
9. If monitor: route to shared monitor output
10. If another playbook also matches: route to combined alert

## 6. Messaging Assets

To be developed separately.

## 7. Decision Tree

### Pattern match logic

Silent Churn fires when the activating signal is corroborated by additional dimensions of absence. The number of additional dimensions required depends on the strength of the activating signal.

### Dimensions of absence

- **Usage:** plateaued, declining, or no activity for 60+ days
- **Users:** declining active user count over 30+ days
- **Activity:** declining login or page view activity over 30+ days
- **Support:** abrupt drop from prior engagement pattern
- **Relationship:** champion inactive or exited, executive sponsor inactive or missing
- **Communication:** one-way (CSM-initiated only) for 60+ days, or no communication at all
- **External:** distress signals (layoffs, being acquired, restructuring)

### Routing rules

- Strong activating signal + 1 or more other dimensions of absence → silent churn hypothesis fires
- Standard activating signal + 2 or more other dimensions of absence → silent churn hypothesis fires
- Strong activating signal alone → recheck scheduled
- Standard activating signal + 1 other dimension of absence → recheck scheduled
- Standard activating signal alone → recheck scheduled

### Recheck windows

- Internal absence signals (usage, users, activity, support, communication): 14 days
- Relationship signals (champion/sponsor changes): 14 days
- External distress signals: 7-10 days
- One recheck only

### Post-recheck

- Additional dimensions of absence now present → hypothesis fires
- Still inconclusive → route to monitor

### Disqualifying patterns (route away from silent churn)

- Red sentiment in last 60 days → not silent, this is visible churn risk handled through other motions
- Active customer-initiated communication with positive engagement → customer is engaged, not silent
- Recent expansion conversation or active renewal discussion → relationship is intact, this is a different motion

### Cross-playbook routing

- If another playbook also matches simultaneously → route to combined alert for human investigation, not standalone Silent Churn hypothesis

### Notes on external distress as activator

External distress alone is not sufficient to fire a hypothesis. A customer can survive layoffs and stay engaged. A customer can be acquired and the new parent expands the contract. The hypothesis requires internal absence to corroborate that the distress is affecting the relationship.

## 8. Success Metrics

### Leading indicators

- Hypothesis acceptance rate by CSMs
- Re-engagement meeting secured with previously inactive stakeholder
- Customer response to CSM outreach following the hypothesis
- New stakeholder identified if original champion is gone

### Lagging indicators

- Renewal closed where silent churn hypothesis was caught and addressed
- Churn avoided vs prior baseline
- Time from signal to first re-engagement conversation
- Reduction in surprise non-renewals

### Expected timeline

- Signal to hypothesis: same day
- Hypothesis to CSM action: within 5 business days
- CSM action to re-engagement attempt: within 10 business days
- Re-engagement to validated relationship status: within 30 days

---

# Playbook 3: Hard Churn Risk

## 1. Objective

Identify accounts where the customer is showing active, visible distress signals at the same time. Surface a hypothesis fast so the CSM can intervene before operational problems become renewal problems.

The goal is to catch customers who are actively struggling — not unhappy customers the CSM already knows about, but customers where the operational pattern indicates risk that may not yet be obvious from any single signal.

## 2. Trigger Criteria

Any single signal activates the agent. The agent investigates corroborating signals before forming a hypothesis. Hard churn fires faster than silent churn because the signals are louder individually, but no single signal alone is enough — even critical tickets and usage anomalies require corroboration to qualify as churn risk.

### Activating signals (any one wakes the agent)

**Internal:**

- Critical or high severity support ticket opened
- Multiple support tickets opened in short window (3+ in 14 days)
- Open critical or high severity ticket past expected resolution window
- Usage spike beyond normal range (could be operational distress, not expansion)
- Plateaued or declining usage with renewal under 90 days
- Champion sudden exit or shift to inactive
- Executive sponsor escalation or shift to inactive
- Sentiment turns red in activity log

**External:**

- Layoffs announced at customer
- Customer acquired (as the acquired party)
- Public restructuring or distress signals
- Loss of leadership relevant to champion or buyer org

## 3. Risk / Why It Matters

Hard churn risk is the loud counterpart to silent churn. Where silent churn happens because nobody noticed, hard churn happens when problems were visible but not connected. A critical ticket is a ticket. A usage spike is a spike. A champion change is a change. Each one alone is normal operational noise. Two of them together, in the right configuration, is a customer in trouble.

The cost of missing the signal is a churn that the team will later say "we saw coming." That's the kind of churn that erodes confidence in the CSM team because the signals were there and nobody pulled the threads.

The cost of mis-firing is also higher than silent churn. Telling a customer they're at risk when they're fine creates exactly the wrong kind of conversation. This is why corroboration matters even for loud signals. One critical ticket plus a healthy customer is just a support issue. One critical ticket plus a usage spike plus renewal in 60 days is a different story.

Speed matters more here than in silent churn. The signals move fast and the window to act is short.

## 4. Required Inputs

The agent must assemble these before producing a hypothesis:

- Support ticket detail for last 90 days: severity, category, status, resolution time
- Open tickets and time-since-open relative to typical resolution
- 90-day utilization trend per contracted product, expressed as percent of contracted usage
- Day-over-day and week-over-week usage changes to detect spikes
- Active user count trend
- Login activity and page view trends
- 60-day activity log: who initiated, sentiment, contact level
- Champion and executive sponsor active status and any recent changes
- Renewal date proximity (under 90 days is a meaningful threshold)
- RSS/external signals within last 90 days
- Recent CSM touch and what was discussed
- Sentiment trajectory in activity log

## 5. Execution Steps

1. Detect activating signal
2. Run signal check across all corroborating distress signal categories: support, usage, relationship, communication, renewal proximity, external
3. Apply pattern match logic (see Decision Tree) to determine output
4. If hypothesis fires: assemble narrative including which signals are firing together, the operational timeline, and what specifically to investigate with the customer
5. Identify the most relevant stakeholder for the situation (champion if relationship-driven, executive sponsor if escalation-warranted)
6. Note renewal proximity as urgency context
7. If recheck scheduled: queue for re-investigation in 3 days
8. If monitor: route to shared monitor output
9. If another playbook also matches (most likely Expansion Ready in cases of growing customer hitting operational issues): route to combined alert

## 6. Messaging Assets

To be developed separately.

## 7. Decision Tree

### Pattern match logic

Hard Churn fires when the activating signal is corroborated by at least one additional distress signal.

### Corroborating distress signals

- **Support:** critical or high severity tickets present, multiple tickets open, tickets past expected resolution time
- **Usage:** spike beyond normal range, decline, plateau below recent baseline
- **Relationship:** champion exit, exec sponsor escalation, recent inactivity from previously engaged stakeholders
- **Communication:** red sentiment in activity log
- **Renewal proximity:** under 90 days
- **External:** layoffs, acquisition as acquired party, restructuring

### Routing rules

- Activating signal + 1 or more corroborating distress signals → hard churn hypothesis fires
- Activating signal alone → recheck scheduled

### Recheck window

- All signals: 3 days
- One recheck only

### Post-recheck

- Corroborating signal now present → hypothesis fires
- Still inconclusive → route to monitor

### Disqualifying patterns (route away from hard churn)

- Activating signal in isolation with no corroboration → not churn, route to monitor after recheck
- Single critical ticket with healthy usage and engaged stakeholders → support issue, not churn risk

### Cross-playbook routing

- Hard Churn and Silent Churn are mutually exclusive by construction. If hard churn fires, silent churn does not. Silent churn requires absence; hard churn requires presence of distress signals (including red sentiment, which disqualifies silent churn).
- If Hard Churn and Expansion Ready both match (growing customer hitting operational issues): route to combined alert for human investigation. This is a real and important combination — fast-growing customers can hit infrastructure or product limits that look like churn risk on one axis and expansion opportunity on the other.

## 8. Success Metrics

### Leading indicators

- Hypothesis acceptance rate by CSMs
- Time from signal to CSM action
- Meeting secured with relevant stakeholder within 5 business days
- Resolution path established for active distress

### Lagging indicators

- Churn avoided in accounts where hard churn was caught and addressed
- Renewal closed where hard churn was caught early
- Reduction in churns the team "saw coming"
- Time from first distress signal to remediation

### Expected timeline

- Signal to hypothesis: same day
- Hypothesis to CSM action: within 2 business days (faster than expansion or silent churn)
- CSM action to customer conversation: within 5 business days
- Customer conversation to remediation plan: within 14 days
