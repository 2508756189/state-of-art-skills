---
name: git-push-guard
description: Use when preparing commits or pushes to TianyiParking or研发云 git remotes, especially when the target branch is unclear, when a push may affect production branches, or when the assistant should ask for required repo and branch details before pushing.
---

# Git Push Guard

## Overview

先确认，再提交，再推送。这个 skill 用来避免默认推到错误分支，尤其是研发云、TianyiParking 这类多分支仓库。

## Workflow

1. 先收集必要信息：仓库路径、目标远端、当前分支、目标分支、是否已有提交、是否允许我创建提交。
2. 只要目标分支没明确，就先问“推送到哪个分支”。默认不要猜 `master`、`main` 或 `release`。
3. 先执行 `git status --short --branch` 和 `git remote -v`，再决定是提交、rebase、cherry-pick 还是直接推送。
4. 推送前复核 commit hash 和 branch name，推送后复核远端 heads，确认已到目标分支。
5. 如果远端拒绝或校验失败，先读报错，再修正作者信息、分支或提交内容，不要盲目重试。

## Questions To Ask

信息不全时，优先一次问清这几项：
- 目标仓库是哪个。
- 目标分支是哪个。
- 需要我只推送，还是也要帮你创建提交。
- 是否允许改写历史，还是只允许普通推送。
