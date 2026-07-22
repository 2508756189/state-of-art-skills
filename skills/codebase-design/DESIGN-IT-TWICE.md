# Design It Twice

When the user wants to explore alternative interfaces for a chosen deepening candidate, compare multiple designs. Based on "Design It Twice" (Ousterhout) — your first idea is unlikely to be the best. Parallel sub-agents are optional and require explicit user approval and runtime support.

Uses the vocabulary in [SKILL.md](SKILL.md) — **module**, **interface**, **seam**, **adapter**, **leverage**.

## Process

### 1. Frame the problem space

Before generating alternatives, write a user-facing explanation of the problem space for the chosen candidate:

- The constraints any new interface would need to satisfy
- The dependencies it would rely on, and which category they fall into (see [DEEPENING.md](DEEPENING.md))
- A rough illustrative code sketch to ground the constraints — not a proposal, just a way to make the constraints concrete

Show this to the user and confirm whether they want more alternatives or a direct recommendation.

### 2. Generate alternatives

Generate at least two materially different interfaces. Use sub-agents only when the user requests them and the runtime exposes a suitable agent tool; otherwise reason through the alternatives in the current task.

For each alternative, use a separate technical brief (file paths, coupling details, dependency category from [DEEPENING.md](DEEPENING.md), what sits behind the seam). Give each design a different constraint:

- Alternative 1: "Minimize the interface — aim for 1–3 entry points max. Maximise leverage per entry point."
- Alternative 2: "Maximise flexibility — support many use cases and extension."
- Alternative 3: "Optimise for the most common caller — make the default case trivial."
- Alternative 4 (if applicable): "Design around ports & adapters for cross-seam dependencies."

Include both [SKILL.md](SKILL.md) vocabulary and CONTEXT.md vocabulary in the brief so each alternative uses the architecture language and the project's domain language consistently.

Each alternative should include:

1. Interface (types, methods, params — plus invariants, ordering, error modes)
2. Usage example showing how callers use it
3. What the implementation hides behind the seam
4. Dependency strategy and adapters (see [DEEPENING.md](DEEPENING.md))
5. Trade-offs — where leverage is high, where it's thin

### 3. Present and compare

Present designs sequentially so the user can absorb each one, then compare them in prose. Contrast by **depth** (leverage at the interface), **locality** (where change concentrates), and **seam placement**.

After comparing, give your own recommendation: which design you think is strongest and why. If elements from different designs would combine well, propose a hybrid. Be opinionated — the user wants a strong read, not a menu.
