# Taste Skill

Use this skill when the user wants design judgment, not just functional UI.

## Source

Inspired by Taste Skill: `https://github.com/leonxlnx/taste-skill` (MIT).

This local version is adapted for Codex and Claude style frontend work.

## Principles

- Start from the product's actual job, audience, and usage frequency.
- Make the first screen useful, not merely decorative.
- Use spacing, hierarchy, and state design to clarify work.
- Avoid generic SaaS sameness: excessive cards, purple gradients, decorative blobs, and fake marketing hero layouts.
- Use real data paths and visible loading/error/success states.
- Make controls feel native to the task: icons for tools, toggles for binary choices, tabs for views, sliders/inputs for numeric values.
- Keep text inside its containers at mobile and desktop sizes.

## Review Pass

When polishing a UI, inspect:

1. First impression: can the user tell what this is and what they can do?
2. Hierarchy: does the eye land in the right order?
3. Density: is this dashboard/tool compact enough for repeated use?
4. States: loading, empty, error, success, disabled, hover, active, selected.
5. Responsiveness: no clipped text, overlap, layout jumping, or unusable tiny controls.
6. Specificity: visuals and copy should fit the domain, not feel like a template.

## Final Verification

For frontend changes, verify with a running app or browser screenshot when possible. Do not claim polish from code inspection alone if rendering is cheap to check.
