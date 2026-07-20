# Pinia Testing Patterns

Use these patterns after checking the project's installed Pinia,
`@pinia/testing`, Vue Test Utils, and Vitest versions.

## Pure Store Test

```ts
import { beforeEach, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

beforeEach(() => {
  setActivePinia(createPinia());
});

it("updates public state", () => {
  const store = useCounterStore();
  store.increment();
  expect(store.n).toBe(1);
});
```

## Component With Stubbed Actions

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

## Execute Real Actions

```ts
createTestingPinia({
  createSpy: vi.fn,
  stubActions: false,
});
```

## Seed Initial State

```ts
createTestingPinia({
  createSpy: vi.fn,
  initialState: {
    counter: { n: 10 },
    profile: { name: "Sherlock Holmes" },
  },
});
```

## Add A Plugin Under Test

```ts
createTestingPinia({
  createSpy: vi.fn,
  plugins: [myPiniaPlugin],
});
```

## Override And Reset A Getter

```ts
const pinia = createTestingPinia({ createSpy: vi.fn });
const store = useCounterStore(pinia);

store.double = 42;
expect(store.double).toBe(42);

// @ts-expect-error test-only reset
store.double = undefined;
```

## Mounting Decision

- Prefer `mount()` when child behavior is part of the confidence boundary.
- Prefer targeted stubs when only one or two child components are irrelevant.
- Use `shallow: true` when complete child isolation is the explicit test goal.
- Recheck slots and integration behavior when moving from mount to shallow.
