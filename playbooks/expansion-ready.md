**Implementation note:** This playbook references signals (active user counts, login activity, page views, new contacts within 30 days, contact title/function) that are not yet available in the simulated dataset. The agent should treat references to these signals as currently unavailable and rely on the available signals: utilization trends, feature breadth, sentiment trajectory, CSM activity patterns, support ticket character, champion/exec engagement status, and external RSS signals.

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
