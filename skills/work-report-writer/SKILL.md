---
name: work-report-writer
description: Use when the user asks Codex to整理周报、工作项、领导汇报、上线说明、变更记录、复盘材料，or to compress scattered recent work into a concise Chinese report. Especially useful when the final audience may require either a structured internal report or a single leadership-facing paragraph while preserving factual provenance, dates, scope, rollout evidence, risks, follow-up, and rollback notes.
---

# Work Report Writer

Use this skill to turn scattered work history, user edits, rollout notes, or conversation context into a useful Chinese work report without losing the factual spine.

## Workflow

1. Confirm the reporting period and audience from the user's wording.
   - If the user mentions 上周、本周、领导、一段话, preserve that exact scope and format.
   - If prior work items cross weeks, separate them by actual completion or rollout date before drafting.
2. Gather only evidence needed for the report.
   - Prefer user-provided notes, recent Codex summaries, rollout summaries, saved Markdown drafts, and concrete deployment or verification paths.
   - Do not invent results; mark unclear items as待确认 or omit them from a final leadership paragraph.
3. Draft in two layers when useful.
   - Internal draft: background, scope, completed work, verification, risks, next steps, rollback.
   - Leadership version: one concise paragraph focused on progress, impact, and remaining risk.
4. Preserve user edits.
   - When the user says they modified a report, read or use their edited version as the source of truth.
   - Tighten wording and structure without replacing their factual framing.
5. End with the requested form, not every possible form.
   - If the user asks for 一段话, output one paragraph only.
   - If the user asks for 工作项, keep reusable sections such as背景、范围、变更、验证、后续、回滚.

## Style Rules

- Lead with completed progress and concrete impact.
- Keep Chinese business wording formal but not inflated.
- Use exact project, lot, system, date, host, backup path, or file path only when available from evidence.
- Avoid overclaiming production success when verification is partial or blocked.
- Compress repetitive debugging detail into the outcome and evidence.

## Useful Templates

### Structured Work Item

```markdown
## 背景

## 处理范围

## 本次变更

## 发布与验证
## 风险与后续
## 回滚方式
```

### Leadership Paragraph

```text
本周主要完成……，重点推进……；目前……已完成/已验证，……仍需继续跟进，下一步将……。
```
