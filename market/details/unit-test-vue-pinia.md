# Unit Test Vue Pinia

Use this skill to create or review unit tests for Vue components, composables,
and Pinia stores. Keep tests small, deterministic, and behavior-first.

## Workflow

1. Confirm the project versions and whether `@pinia/testing` is installed.
2. Identify the behavior boundary: component UI, composable, or store behavior.
3. Choose the narrowest test style and Pinia setup that proves the behavior.
4. Drive the test through public inputs such as props, form updates, clicks,
   emitted child events, and store APIs.
5. Assert observable outputs and side effects before considering an
   instance-level assertion.
6. Run the focused Vitest target and report any remaining coverage gap.

## Core Rules

- Test one behavior per test.
- Prefer rendered output, emitted events, callback calls, store state changes,
  and persisted side effects over implementation details.
- Access `wrapper.vm` only when no reasonable DOM, prop, emit, or store-level
  assertion can express the behavior.
- Reset mocks and mutable browser storage between tests.
- Keep fixture data minimal and deterministic.
- Do not introduce `@pinia/testing` into a project just to test a pure store.

## Choose The Pinia Setup

### Pure store behavior

Use a fresh real Pinia when testing store state transitions or actions without
component rendering:

```ts
import { beforeEach, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

beforeEach(() => {
  setActivePinia(createPinia());
});

it("increments", () => {
  const counter = useCounterStore();
  counter.increment();
  expect(counter.n).toBe(1);
});
```

### Component with stubbed store actions

Use `createTestingPinia()` only when `@pinia/testing` is already available or
the user explicitly approves adding that development dependency:

```ts
import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { vi } from "vitest";

const wrapper = mount(ComponentUnderTest, {
  global: {
    plugins: [createTestingPinia({ createSpy: vi.fn })],
  },
});
```

Actions are stubbed by default. Keep that default when the component test only
needs to verify that an action was called.

### Component that must execute real actions

Use `stubActions: false` only when the behavior inside the action is part of
the test:

```ts
createTestingPinia({
  createSpy: vi.fn,
  stubActions: false,
});
```

### Seed store state

```ts
createTestingPinia({
  createSpy: vi.fn,
  initialState: {
    counter: { n: 20 },
    user: { name: "Leia Organa" },
  },
});
```

### Add a Pinia plugin

Pass plugins through `createTestingPinia({ plugins: [...] })`. For a real
Pinia, remember that plugins run only after Pinia is installed on a Vue app.

### Getter override for edge cases

```ts
const pinia = createTestingPinia({ createSpy: vi.fn });
const store = useCounterStore(pinia);

store.double = 999;
// @ts-expect-error test-only reset of an overridden getter
store.double = undefined;
```

## Vue Test Utils Approach

- Start with `mount()` when rendering the real child behavior provides useful
  confidence.
- Use targeted `global.stubs` for irrelevant or expensive children.
- Use `shallow: true` only when full child isolation is the purpose of the
  test; note that excessive stubbing makes the test less production-like and
  can hide slot or integration behavior.
- Trigger behavior through props and user-like interactions.
- Use `findComponent(...).vm.$emit(...)` when a child stub must emit an event.
- Await Vue updates or promises only when the behavior is asynchronous.
- Assert emitted events and payloads with `wrapper.emitted(...)`.

## Key Snippets

Emit and assert a payload:

```ts
await wrapper.find("button").trigger("click");
expect(wrapper.emitted("submit")?.[0]?.[0]).toBe("Mango Mission");
```

Update a form and assert its public output:

```ts
await wrapper.find("input").setValue("Agent Violet");
await wrapper.find("form").trigger("submit");
expect(wrapper.emitted("save")?.[0]?.[0]).toBe("Agent Violet");
```

## Review Checklist

- Does each test describe one observable behavior?
- Is the Pinia instance reset for every test?
- Are mocks, timers, storage, and network doubles reset deterministically?
- Are real actions enabled only when their implementation is under test?
- Are selectors and assertions resilient to refactors?
- Does the test avoid unnecessary snapshots and large-object equality checks?
- Does the focused Vitest command pass in the real project?

## Output Contract

- For create or update work, return the finished test plus a short note about
  the selected Pinia strategy and the exact verification command.
- For review work, return concrete findings first, followed by missing
  coverage or brittleness risks.
- State any dependency or version assumption that affects the recommendation.

## Source And Local Curation

Adapted from GitHub's `github/awesome-copilot` skill
`skills/unit-test-vue-pinia` at commit
`314cf968ab643bc0ad1488e98e6e7893b752004a` under the repository MIT license.
The local overlay removes unsupported frontmatter, makes dependency checks
explicit, and aligns mount-versus-shallow guidance with the official Pinia and
Vue Test Utils documentation.

## Risk And Runtime Limits

- This skill does not install dependencies or run tests without the normal
  project-level authorization.
- Pinia and Vue Test Utils APIs can change; verify the installed package
  versions before applying examples mechanically.
- JSDOM tests do not prove browser layout, accessibility, or full end-to-end
  behavior. Use the existing browser-testing workflow for those concerns.
- The realistic minimum smoke test is a focused Vitest run of a real Pinia
  store or component test in the target repository.

## References

- `references/pinia-patterns.md`
- <https://pinia.vuejs.org/cookbook/testing.html>
- <https://test-utils.vuejs.org/guide/>
- <https://test-utils.vuejs.org/guide/advanced/stubs-shallow-mount.html>
