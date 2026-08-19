---
name: software-product-brochure
description: Use when designing, critiquing, or rewriting a software/SaaS/enterprise platform product brochure, solution brief, product overview, or sales leave-behind. Applies especially when deciding what information belongs in a brochure versus product docs, technical docs, pitch decks, or implementation manuals.
---

# Software Product Brochure Design

Use this skill to create software product brochures that make a buyer understand the product quickly, care about it, and trust it enough to continue a sales or evaluation conversation.

## Core Rule

A software brochure is not a feature dump, technical architecture document, or pitch deck. It is a buyer-facing explanation of:

1. who the product is for,
2. what painful situation it resolves,
3. what outcome changes after adoption,
4. what capabilities make that outcome possible,
5. why the buyer can trust the product,
6. how to start or deploy.

## Required Workflow

1. Identify the buyer and evaluator roles.
   - Business buyer: cares about outcomes, risk, efficiency, governance, ROI, and adoption.
   - Operator/admin: cares about workflow, manageability, compliance, reporting, and support.
   - Technical evaluator: cares about deployment model, integration, security, extensibility, and data control.
2. Write a one-sentence product position before designing pages.
   - Format: `For [audience], [product] is a [category] that helps [outcome] by [mechanism].`
3. Build the brochure around buyer comprehension.
   - First answer "why this exists".
   - Then show the product loop or scenario flow.
   - Then show capabilities grouped by user task.
   - Then show credibility and deployment path.
4. Separate brochure content from technical documentation.
   - Brochure: categories, outcomes, workflows, proof, scenarios.
   - Technical appendix only when necessary: integration categories, deployment options, security posture, compatibility.
   - Never lead with stack names, ports, API endpoints, database schemas, service internals, or implementation tasks.
5. Keep claims evidence-aware.
   - Use concrete but supportable claims.
   - Avoid invented numbers, unverifiable superiority, or "industry-leading" without proof.
6. End with a clear next step.
   - Demo, pilot, deployment consultation, contact, or implementation assessment.

## Recommended Brochure Structure

Use 8-12 pages for a formal product brochure:

1. Cover: product name, category, audience, transformation promise.
2. Why now: market/context pains in the buyer's language.
3. Product at a glance: product loop or capability map.
4. Scenario flow: how a real user moves through the product.
5. Capability modules: 4-6 grouped modules, each tied to an outcome.
6. Role value: buyer/admin/operator/end-user benefits.
7. Differentiators: 3-5 reasons the product is different, written as practical advantages.
8. Trust: security, governance, data control, deployment, reliability, support.
9. Use cases: 3-5 scenarios with "before -> after" framing.
10. Getting started: pilot/deployment path and next step.
11. Optional appendix: technical compatibility and architecture categories.

## What To Include

- Product category and positioning.
- Target audience and buyer roles.
- Problem statements that the audience recognizes.
- Product loop, workflow, or scenario diagram.
- Capability groups in plain language.
- Outcomes and value by role.
- Use cases and deployment contexts.
- Security/governance/data-control posture if relevant.
- Integration/deployment model at a category level.
- Proof points, customer evidence, or measurable value only when sourced.
- Clear next action.

## What Not To Include

- Internal technology stack in the opening pages.
- Detailed technology route, code architecture, API paths, port numbers, table names, package names, class names, or database credentials.
- Unexplained acronyms and vendor/model names unless buyer-relevant.
- Roadmap items presented as currently available.
- Exhaustive feature lists without scenario grouping.
- Technical jargon used to compensate for weak value clarity.
- Implementation instructions, install commands, or admin manuals.
- Dense screenshots that require zooming or training to understand.
- Generic claims such as "AI empowered", "one-stop", "industry-leading", "closed loop" without explaining the buyer-visible change.
- Pricing, unless the brochure's purpose is a price/package sheet.

## Technical Content Placement

Use this rule:

- Main pages: "private deployment", "real-time audio/video", "AI analysis", "data governance", "system integration".
- Technical appendix: deployment topology, integration surfaces, data/security posture, supported environments.
- Separate technical doc: framework names, API details, database schema, deployment commands, model prompts, ports, logs.

For early-stage products, a technical appendix is often better than putting stack names in the main story. It reassures evaluators without distracting business buyers.

## Page Writing Pattern

For each page, use:

- Page title: buyer-recognizable idea, not internal module name.
- Lead sentence: one clear outcome.
- Body: 3-5 grouped points or a simple matrix.
- Visual: flow, map, before/after, role matrix, or proof block.
- Avoid more than one dense table per page.

## Tone

Formal, direct, credible. Prefer "helps organizations standardize review workflows" over "empowers next-generation intelligent evaluation ecology".

## References

For the benchmark used to derive these rules, see `references/software_product_brochure_benchmark.md`.
