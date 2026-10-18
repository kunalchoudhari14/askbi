# Feature Specification: Default Dashboard (v0-c)

**Feature Branch**: `v0c-static-dashboard`

**Created**: 2026-10-18

**Status**: Draft

**Input**: User description: "v0-c: the default Dashboard page for AskBI. Both roles see the same dashboard after logging in: 4 KPI cards (Revenue, Orders, AOV, Late-delivery %) and 2 charts (monthly revenue trend, Top 10 product categories by revenue), with visible KPI definitions. Monthly revenue summed over the full range must equal the Revenue card. Out of scope: filters, date pickers, orders-by-status chart, AI features, row-level security."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the headline KPIs at a glance (Priority: P1)

A logged-in user (end user or developer) opens the Dashboard and immediately sees four KPI cards: Revenue, Orders, Average order value (AOV) and Late-delivery %. Each number follows the shared definitions, so the user can trust and quote it.

**Why this priority**: The KPI cards are the fastest, most-used summary of marketplace health. On its own, this story replaces the current placeholder with something useful.

**Independent Test**: Log in as each role, open the Dashboard, and compare each card against an independent hand calculation on the dataset.

**Acceptance Scenarios**:

1. **Given** a logged-in user of either role, **When** they open the Dashboard, **Then** they see four cards labelled Revenue, Orders, Average order value and Late-delivery %.
2. **Given** the dataset, **When** the Revenue card is shown, **Then** it equals the sum of item prices of all valid orders (freight excluded), shown in BRL with the "R$" symbol.
3. **Given** the dataset, **When** the Orders card is shown, **Then** its main number is the count of ALL orders, and a smaller line underneath shows how many of them are canceled or unavailable.
4. **Given** the dataset, **When** the AOV card is shown, **Then** it equals Revenue divided by the number of valid orders, in R$.
5. **Given** the dataset, **When** the Late-delivery % card is shown, **Then** it equals delivered orders that reached the customer on a later calendar day than the estimated delivery date, divided by all delivered orders with a known delivery date, shown as a percentage.
6. **Given** a delivered order that reached the customer on the same calendar day as its estimate, **When** Late-delivery % is calculated, **Then** that order counts as on time.

---

### User Story 2 - Understand how revenue moves over time (Priority: P2)

The user sees a monthly revenue trend chart covering the full date range of the data, so they can spot growth, seasonality and unusual months.

**Why this priority**: Trend is the next question after "how big is it?", but the KPI cards already deliver value without it.

**Independent Test**: Open the Dashboard and check that the chart shows one point per month from the first to the last month in the data, and that the monthly values add up exactly to the Revenue card.

**Acceptance Scenarios**:

1. **Given** the dataset, **When** the monthly revenue chart is shown, **Then** it covers every calendar month from the earliest to the latest order month, in time order.
2. **Given** a month with no valid orders inside the range, **When** the chart is shown, **Then** that month appears with zero revenue rather than being skipped.
3. **Given** the chart's monthly values, **When** they are added up, **Then** the total equals the Revenue card exactly (to the cent).
4. **Given** the user hovers over or inspects a month, **When** the value is shown, **Then** it displays the month and its revenue in R$.

---

### User Story 3 - See which product categories drive revenue (Priority: P3)

The user sees a chart of the 10 product categories with the highest revenue, labelled with English category names, and titled so it is clear only the top 10 are shown.

**Why this priority**: Category mix is valuable context, but less central than the totals and the trend.

**Independent Test**: Open the Dashboard and compare the chart's 10 categories and values against an independent ranking of category revenue on the dataset.

**Acceptance Scenarios**:

1. **Given** the dataset, **When** the category chart is shown, **Then** it shows exactly 10 categories, ordered from highest to lowest revenue.
2. **Given** the category chart, **When** the user reads its title, **Then** the title contains "Top 10".
3. **Given** a category with an English translation, **When** it appears in the chart, **Then** it is labelled with the English name.
4. **Given** the category chart, **When** a bar's value is read, **Then** it equals the sum of item prices in that category across valid orders, in R$.

---

### User Story 4 - Find out what each number means (Priority: P2)

The user can see, on the Dashboard itself, how each KPI and chart is defined (what counts as a valid order, what is in revenue, how lateness is judged), so they can explain the numbers to others.

**Why this priority**: The dashboard's goal is a *trustworthy* overview; numbers that cannot be explained are not trusted. It is small but required for the feature to meet its purpose.

**Independent Test**: Open the Dashboard and, without leaving the page or asking anyone, find the definition for each of the four KPIs and both charts.

**Acceptance Scenarios**:

1. **Given** the Dashboard is open, **When** the user looks for what "Revenue" means, **Then** they can find the definition on the page in at most one click (e.g. a visible note, tooltip or expandable section).
2. **Given** the definitions shown, **When** compared with the rules used for the numbers, **Then** they match: valid orders exclude canceled and unavailable; revenue is item prices only, freight excluded, in BRL; late means delivered on a later day than estimated, same day is on time.

---

### Edge Cases

- **Delivered orders with no delivery date** (8 in the current data): they cannot be judged late or on time, so they are left out of both the top and bottom of Late-delivery %. The definition on the page says so.
- **Products with no category** (about 610 products): their revenue is grouped under one label, "Unknown category", which competes for the top 10 like any other category. Their revenue is never dropped, so it still counts in Revenue and the monthly trend.
- **Categories with no English translation** (2 in the current data): shown with their original category name, so they are never hidden or blank.
- **Months with no orders inside the range** (e.g. Nov 2016): shown as zero, so the trend's timeline has no gaps.
- **Very sparse edge months** (e.g. Sep 2016, Dec 2016, Sep 2018 have only 1–2 valid orders): still shown, because dropping them would break the rule that monthly revenue adds up to the Revenue card.
- **Valid orders with no items**: they add nothing to revenue but still count as valid orders in the AOV denominator, following the definition as written.
- **Database missing or unreadable**: the Dashboard shows a clear message telling the user the data is unavailable (and, for a developer, that it can be rebuilt), instead of crashing or showing zeros.
- **Zero valid orders or zero delivered orders** (possible later, once filters and row-level security narrow the data): AOV and Late-delivery % show "—" (no value) instead of an error or a misleading 0.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Dashboard MUST be the page shown to both roles (end_user and developer) after login, with identical content for both.
- **FR-002**: The system MUST apply one shared set of definitions everywhere on the Dashboard:
  - *Valid order*: an order whose status is not "canceled" or "unavailable".
  - *Revenue*: sum of item prices of valid orders; freight/shipping excluded; currency BRL (R$).
  - *Delivered order*: an order whose status is "delivered".
- **FR-003**: The system MUST show a **Revenue** card equal to Revenue as defined in FR-002.
- **FR-004**: The system MUST show an **Orders** card whose main number is the count of all orders (every status), with a secondary line showing the count of canceled plus unavailable orders.
- **FR-005**: The system MUST show an **Average order value** card equal to Revenue divided by the number of valid orders.
- **FR-006**: The system MUST show a **Late-delivery %** card equal to (delivered orders whose customer delivery date is a later calendar day than the estimated delivery date) ÷ (delivered orders with a known customer delivery date). Same-day delivery counts as on time. Delivered orders with no delivery date are excluded from both parts.
- **FR-007**: The system MUST show a **monthly revenue trend** chart with one value per calendar month from the earliest to the latest order month in the data, including zero-revenue months inside that range. Orders are assigned to a month by their purchase date.
- **FR-008**: The sum of all monthly revenue values MUST equal the Revenue card exactly.
- **FR-009**: The system MUST show a **Top 10 product categories by revenue** chart, ranked highest first, with the words "Top 10" in its title. Category revenue uses the same Revenue definition (item prices of valid orders).
- **FR-010**: Category labels MUST use English category names; categories without a translation use their original name, and products with no category are grouped as "Unknown category".
- **FR-011**: Money values MUST be shown in BRL with the "R$" symbol; large values may be abbreviated on cards (e.g. "R$ 13.2M") as long as the full value is available on the page. Late-delivery % MUST be shown as a percentage with one decimal place.
- **FR-012**: The Dashboard MUST make the definition of each KPI and each chart visible on the page or reachable in at most one click, and those definitions MUST match FR-002 to FR-010.
- **FR-013**: If the data cannot be loaded, the Dashboard MUST show a clear, friendly error message instead of crashing or showing misleading numbers.
- **FR-014**: If a KPI's denominator is zero, the Dashboard MUST show "—" for that KPI instead of an error or 0.
- **FR-015**: All Dashboard numbers MUST be read from the data through one central data-access point, so future data-scope rules (row-level security, v1) and filters (v0-d) can be applied in one place. The dashboard MUST NOT change any data.
- **FR-016**: The Dashboard MUST NOT include filters, date pickers, an orders-by-status chart, or any AI features in this version.

### Key Entities *(include if feature involves data)*

- **Order**: one customer purchase. Key attributes: status, purchase date, estimated delivery date, actual customer delivery date. Determines valid/delivered and the month.
- **Order item**: one product line within an order. Key attribute: item price (freight is a separate amount and is not revenue). Linked to one order and one product.
- **Product**: a sold item. Key attribute: category (original Portuguese name; may be missing).
- **Category translation**: maps an original category name to its English name.
- **KPI definition**: the plain-language description shown on the Dashboard for each KPI and chart.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For both roles, the Dashboard shows all 4 KPI cards and both charts within 3 seconds of opening the page on a typical laptop, and within 1 second on later visits in the same session.
- **SC-002**: 100% of displayed KPI values match an independent hand calculation on the same dataset (money to the cent before rounding for display; percentage to one decimal place).
- **SC-003**: The monthly revenue values add up to the Revenue card with a difference of R$ 0.00.
- **SC-004**: A first-time user can find the definition of any KPI on the page in under 15 seconds, without help.
- **SC-005**: The Top 10 chart shows exactly 10 categories, all with readable English (or original) labels, and no blank labels.
- **SC-006**: An end user and a developer see identical numbers and charts on the Dashboard.

## Assumptions

- The dataset is the static Olist snapshot already loaded into the app's database (orders from Sep 2016 to Oct 2018); no live updates are expected.
- "Full date range" means from the month of the earliest order purchase to the month of the latest, across all orders, not only valid ones. The latest months may look like a sharp drop because the snapshot ends there; this is expected and not hidden.
- Months are assigned by order purchase date (not approval or delivery date), which is the standard choice for revenue trends on this dataset.
- Lateness is judged by calendar date only (time of day ignored), which is how "same day counts as on time" is applied.
- No returns or refunds exist in the data, so no net revenue is calculated.
- Both roles see the full dataset for now; row-level security (data scope) arrives in v1 and will plug into the central data-access point (FR-015).
- Existing login and navigation (v0-b) are reused unchanged; the Dashboard page is already listed first for both roles.
- Chart type for each chart (e.g. line vs. bar) is a design choice left to planning, as long as the requirements above hold.
