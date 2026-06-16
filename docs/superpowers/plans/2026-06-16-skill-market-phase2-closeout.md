# Phase 2 (Skill Market) 接入闭环上线 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把已写好但未上线/未验证的 Skill Market 接入闭环打通上线，达到国内现场可演示状态。

**Architecture:** 两个仓库协同——`state-of-art-skills`（能力仓库，托管 registry + zip 包）作为数据源，`sub2api` fork 的连接器弹窗通过 fetch 拉取 registry、生成带 sha256 校验的安装脚本。无后端。codex 已写完 ~90% 代码，本计划只做：提交上线 + 修 python 依赖坑 + 补回归测试 + 改 registry CDN + 真机验证。

**Tech Stack:** Python 3（registry 构建）、Vue3 + TypeScript + Vite + Vitest + pnpm（fork 前端）、Docker（fork 镜像）、jsDelivr CDN、GitHub Actions（CI）。

**Spec:** `docs/superpowers/specs/2026-06-16-skill-market-phase2-closeout-design.md`

**两个工作树（务必分清）：**
- skill 仓库工作树: `C:\Users\王曙辉\ZCodeProject\state-of-art-skills`
- fork 工作树: `C:\Users\王曙辉\ZCodeProject\sub2api`

---

## File Structure

### state-of-art-skills（本计划只提交，不改逻辑）
- 提交（已存在、未跟踪）: `market/schema.v1.json`, `market/categories.json`, `market/index.json`, `scripts/build_market.py`, `scripts/test_build_market.py`, `.github/workflows/validate-market.yml`, `dist/skills/*.zip`(12), `docs/superpowers/**`
- 修改: `.gitignore`, `README.md`

### sub2api fork
- 修改 `src/components/keys/connectorTemplates.ts`（坑 2：python→unzip，2 处）
- 修改 `src/api/skillMarket.ts`（坑 4：默认 URL 改 jsDelivr）
- 修改 `src/components/keys/__tests__/connectorTemplates.spec.ts`（坑 3：补 skill 回归测试）
- 提交已存在的工作区改动（`SkillMarketSelector.vue`, `skillMarket.ts` 等，codex 已写好）

---

## Task 1: skill 仓库本地校验 + 重新构建产物

**Files:**
- Verify: `C:\Users\王曙辉\ZCodeProject\state-of-art-skills\` 全部产物

- [ ] **Step 1: 跑单测确认构建器正确**

Run（cmd 或 powershell）:
```
cd /d C:\Users\王曙辉\ZCodeProject\state-of-art-skills
python scripts\test_build_market.py
```
Expected: `OK`（3 个测试全过：构建+zip+checksum、重名拒绝、泄密拒绝）。若 `python` 不存在用 `py` 或 `python3`。

- [ ] **Step 2: 重新构建 registry + zip，确保产物最新**

Run:
```
cd /d C:\Users\王曙辉\ZCodeProject\state-of-art-skills
python scripts\build_market.py
```
Expected: 输出 JSON `{"skills": 12, "write": true}`，`dist/skills/` 下 12 个 zip，`market/index.json` 更新。

- [ ] **Step 3: 校验 git 工作区产物是否与重新构建一致**

Run:
```
cd /d C:\Users\王曙辉\ZCodeProject\state-of-art-skills
git status --short
```
Expected: 重新构建后 `market/index.json` 和 `dist/skills/*.zip` **无新增改动**（产物已是最新）。若 `index.json` 显示 `M`，说明之前产物过期，本步已修正；继续。若 `dist/` 下 zip 变化，同理。

- [ ] **Step 4: 不提交，留给 Task 2 一起**

---

## Task 2: skill 仓库提交并推送

**Files:**
- Modify: `.gitignore`, `README.md`
- Add: `market/`, `scripts/`, `.github/`, `dist/skills/*.zip`, `docs/superpowers/`

- [ ] **Step 1: 确认 .gitignore 已含 dist zip 负向豁免**

读 `C:\Users\王曙辉\ZCodeProject\state-of-art-skills\.gitignore`，确认含:
```
*.zip
!dist/skills/*.zip
```
codex 已写好。若缺则补上（这两行是 zip 能进 git 的关键）。

- [ ] **Step 2: 更新 README，补 Skill Market 章节**

在 `README.md` 末尾追加（若已无此章节）:

```markdown
## Skill Market (Phase 2)

This repo is consumed as a **skill registry** by the Sub2API fork's "Use API Key" dialog.

- `market/index.json` — machine-readable registry (schema `market/schema.v1.json`), one entry per skill with `archive.path` / `sha256` / `size`.
- `dist/skills/<id>.zip` — packaged skill, byte-identical to `skills/<id>/` contents.
- `scripts/build_market.py` — rebuild registry + zips. Run it after any skill change, commit the regenerated `market/index.json` + zips. CI (`validate-market.yml`) rejects PRs where products are stale.
- Consumers fetch the registry from jsDelivr: `https://cdn.jsdelivr.net/gh/2508756189/state-of-art-skills@main/market/index.json`.

Install targets per runtime: `~/.codex/skills/<id>`, `~/.claude/skills/<id>`, `~/.agents/skills/<id>` (portable).
```

- [ ] **Step 3: 暂存所有 skill market 相关文件**

Run:
```
cd /d C:\Users\王曙辉\ZCodeProject\state-of-art-skills
git add .gitignore README.md market scripts .github dist docs
```

- [ ] **Step 4: 确认暂存内容，无意外文件**

Run:
```
git status --short
```
Expected: 看到 `market/`, `scripts/`, `.github/workflows/validate-market.yml`, `dist/skills/*.zip`(12), `docs/superpowers/`, `.gitignore`, `README.md` 全在暂存区。**不应**出现 `.env`、`__pycache__`、`*.pyc`（gitignore 已排除）。

- [ ] **Step 5: 提交**

Run:
```
git commit -m "feat(market): skill market registry, builder, CI, and packaged skills

- market/schema.v1.json + index.json + categories.json
- scripts/build_market.py (zip + sha256 + secret scan) + unit tests
- .github/workflows/validate-market.yml (test + build + git diff gate)
- dist/skills/*.zip (12 curated skills)
- Phase 2 closeout design spec"
```

- [ ] **Step 6: 推送**

Run:
```
git push origin main
```
Expected: 推送成功。

- [ ] **Step 7: 验证 jsDelivr CDN 可达（国内关键）**

浏览器或 curl 访问:
```
https://cdn.jsdelivr.net/gh/2508756189/state-of-art-skills@main/market/index.json
```
Expected: 返回 JSON，含 12 个 skill。jsDelivr 首次拉取会回源 GitHub，可能需几十秒。若长时间不可达，记下来但继续（不阻塞，后续 Step 真机验证时复查）。

---

## Task 3: fork — 坑 4，registry 默认 URL 改 jsDelivr

**Files:**
- Modify: `C:\Users\王曙辉\ZCodeProject\sub2api\frontend\src\api\skillMarket.ts:3-4`

- [ ] **Step 1: 改默认 URL**

把 `src/api/skillMarket.ts` 第 3-4 行:
```ts
export const DEFAULT_SKILL_MARKET_REGISTRY_URL =
  'https://raw.githubusercontent.com/2508756189/state-of-art-skills/main/market/index.json'
```
改为:
```ts
export const DEFAULT_SKILL_MARKET_REGISTRY_URL =
  'https://cdn.jsdelivr.net/gh/2508756189/state-of-art-skills@main/market/index.json'
```

理由：jsDelivr 国内可直连 + 支持 CORS + 全球 CDN。raw.githubusercontent 作为代码内可覆盖的备选（不改 `loadSkillRegistry` 的可传参签名，保留灵活性）。

- [ ] **Step 2: 若 skillMarket.spec.ts 有硬编码 raw URL 的断言，一并更新**

读 `src/api/__tests__/skillMarket.spec.ts`，搜索 `raw.githubusercontent`。若有断言引用默认 URL，改为 jsDelivr；若只是测 `resolveSkillArchiveUrl` 逻辑（传参测），则不动。

- [ ] **Step 3: 不单独提交，留给 Task 5 一起**

---

## Task 4: fork — 坑 2，安装脚本去掉 python 依赖

**Files:**
- Modify: `C:\Users\王曙辉\ZCodeProject\sub2api\frontend\src\components\keys\connectorTemplates.ts:247-251` 和 `:429-433`

- [ ] **Step 1: Claude 安装脚本 unix 版，python 解压 → unzip**

把 `connectorTemplates.ts` 第 247-251 行（`buildClaudeSkillInstallScript` 内）:
```ts
        'python - "$zip_path" "$(dirname "$target")" <<\'PY\'',
        'import sys, zipfile',
        'with zipfile.ZipFile(sys.argv[1]) as zf:',
        '    zf.extractall(sys.argv[2])',
        'PY',
```
改为:
```ts
        'unzip -o -q "$zip_path" -d "$(dirname "$target")"',
```
（注意缩进与数组前对齐；`unzip -o` 覆盖、`-q` 安静、`-d` 指定目标目录；目标目录父级已由前一行 `mkdir -p "$(dirname "$target")"` 创建）

- [ ] **Step 2: Codex 安装脚本 unix 版，同样改 python → unzip**

把第 429-433 行（`buildCodexInstallScript` 内）相同片段:
```ts
        'python - "$zip_path" "$(dirname "$target")" <<\'PY\'',
        'import sys, zipfile',
        'with zipfile.ZipFile(sys.argv[1]) as zf:',
        '    zf.extractall(sys.argv[2])',
        'PY',
```
改为:
```ts
        'unzip -o -q "$zip_path" -d "$(dirname "$target")"',
```

PowerShell 版本（`Expand-Archive`）不动——它本来就没 python 依赖。

- [ ] **Step 3: 确认无其他 python 残留**

Run（在 fork 工作树）:
```
cd /d C:\Users\王曙辉\ZCodeProject\sub2api\frontend
findstr /S /N "python" src\components\keys\connectorTemplates.ts
```
Expected: 无输出（或仅注释提及）。确认安装脚本里不再调用 python。

- [ ] **Step 4: 不单独提交，留给 Task 5 一起**

---

## Task 5: fork — 坑 3，补 skill 安装脚本回归测试

**Files:**
- Modify: `C:\Users\王曙辉\ZCodeProject\sub2api\frontend\src\components\keys\__tests__\connectorTemplates.spec.ts`

- [ ] **Step 1: 读现有 spec 结构，定位追加位置**

读 `src/components/keys/__tests__/connectorTemplates.spec.ts` 全文，确认导入与 baseline describe 块的位置。在文件末尾追加新 describe。

- [ ] **Step 2: 追加 fixture 和 skill 安装脚本测试**

在文件末尾追加:

```ts
/* ------------------------------------------------------------------ */
/* Skill install script generation (Phase 2)                           */
/* ------------------------------------------------------------------ */

const SKILL_FIXTURE = {
  id: 'markitdown',
  name: 'markitdown',
  archiveUrl: 'https://cdn.jsdelivr.net/gh/acme/skills@main/dist/skills/markitdown.zip',
  sha256: 'e1f4ba4dc95ba61b8989ee68378c54f311a8fafcead2cb7bf673d7762eab098b',
  installTarget: '~/.claude/skills/markitdown',
}

describe('buildAnthropicFiles — skill install script', () => {
  it('emits a bash install script with curl + sha256sum + unzip (no python)', () => {
    const files = buildAnthropicFiles(BASE, KEY, 'unix', {
      ...defaultClaudeOptions(),
      selectedSkills: [SKILL_FIXTURE],
    })
    const script = files[files.length - 1]
    expect(script.path).toBe('Install Claude Code skills (Bash)')
    expect(script.content).toContain('curl -sSLo "$zip_path" "$archive_url"')
    expect(script.content).toContain('sha256sum')
    expect(script.content).toContain('unzip -o -q "$zip_path"')
    expect(script.content).toContain('$HOME/.claude/skills/markitdown')
    expect(script.content).toContain(SKILL_FIXTURE.archiveUrl)
    expect(script.content).toContain(SKILL_FIXTURE.sha256)
    // 关键：不得再依赖 python
    expect(script.content).not.toContain('python')
  })

  it('emits a powershell install script with Invoke-WebRequest + Get-FileHash + Expand-Archive', () => {
    const files = buildAnthropicFiles(BASE, KEY, 'powershell', {
      ...defaultClaudeOptions(),
      selectedSkills: [SKILL_FIXTURE],
    })
    const script = files[files.length - 1]
    expect(script.path).toBe('Install Claude Code skills (PowerShell)')
    expect(script.content).toContain('Invoke-WebRequest')
    expect(script.content).toContain('Get-FileHash -Algorithm SHA256')
    expect(script.content).toContain('Expand-Archive')
  })
})

describe('buildCodexFiles — skill install script', () => {
  const CODEX_SKILL = { ...SKILL_FIXTURE, installTarget: '~/.codex/skills/markitdown' }

  it('emits an install script that writes config.toml/auth.json AND installs skill via unzip', () => {
    const files = buildCodexFiles(BASE, KEY, 'unix', {
      ...defaultCodexOptions(),
      selectedSkills: [CODEX_SKILL],
    }, HINT)
    const script = files[files.length - 1]
    expect(script.path).toBe('Install Codex package (Bash)')
    // 写 config + auth
    expect(script.content).toContain('cat > "$HOME/.codex/config.toml"')
    expect(script.content).toContain('cat > "$HOME/.codex/auth.json"')
    // 装 skill
    expect(script.content).toContain('curl -sSLo "$zip_path" "$archive_url"')
    expect(script.content).toContain('unzip -o -q "$zip_path"')
    expect(script.content).toContain('$HOME/.codex/skills/markitdown')
    expect(script.content).not.toContain('python')
  })
})

describe('regression baseline — empty selectedSkills does not emit install scripts', () => {
  it('claude: default options produce NO install script block', () => {
    const files = buildAnthropicFiles(BASE, KEY, 'unix')
    const paths = files.map((f) => f.path)
    expect(paths).not.toContain('Install Claude Code skills (Bash)')
    expect(paths).not.toContain('Install Claude Code skills (PowerShell)')
  })

  it('codex: default options produce NO install script block', () => {
    const files = buildCodexFiles(BASE, KEY, 'unix', defaultCodexOptions(), HINT)
    const paths = files.map((f) => f.path)
    expect(paths).not.toContain('Install Codex package (Bash)')
    expect(paths).not.toContain('Install Codex package (PowerShell)')
  })
})
```

- [ ] **Step 3: 跑测试，确认新断言通过 + 旧的不回归**

Run:
```
cd /d C:\Users\王曙辉\ZCodeProject\sub2api\frontend
pnpm test
```
Expected: 全绿（原 10 个 baseline 断言 + 新增 skill 断言）。若新断言失败，按失败信息修 `connectorTemplates.ts`（通常是字符串拼接/路径不符）。**特别注意 `not.toContain('python')` 必须通过——这是坑 2 的回归保护。**

- [ ] **Step 4: 不单独提交，留给 Task 6 一起**

---

## Task 6: fork — 提交所有 skill market 改动并构建镜像

**Files:**
- Commit 全部工作区改动（codex 的 + Task 3/4/5 的）

- [ ] **Step 1: 查看工作区，确认改动范围**

Run:
```
cd /d C:\Users\王曙辉\ZCodeProject\sub2api\frontend
git status --short
```
Expected: `SkillMarketSelector.vue`, `skillMarket.ts`, `skillMarket.spec.ts`, `connectorTemplates.ts`, `connectorTemplates.spec.ts`, `connectorPresets.ts`, `ConnectorOptions.vue`, `UseKeyModal.vue`, `KeysView.vue`, `zh.ts`, `en.ts` 等。

- [ ] **Step 2: 暂存全部相关改动**

Run（在 fork 根目录）:
```
cd /d C:\Users\王曙辉\ZCodeProject\sub2api
git add frontend/src
```

- [ ] **Step 3: 提交**

Run:
```
git commit -m "feat(keys): integrate TokenPort skill market into Use API Key dialog

- fetch registry (jsDelivr CDN) + select skills in dialog
- generate bash/powershell install scripts with sha256 verification (unzip, no python)
- regression tests for skill install scripts + baseline parity"
```

- [ ] **Step 4: 构建镜像**

Run:
```
docker build -t sub2api-fork:dev C:\Users\王曙辉\ZCodeProject\sub2api
```
Expected: 多阶段构建（frontend pnpm build → go build embed → runtime）成功。若失败，看报错；常见是 pnpm install 网络问题，重试。

- [ ] **Step 5: 推送 fork（可选，留历史）**

Run:
```
git push origin <当前分支>
```
（fork 分支名按实际，常见 `feat/connector-customization` 或 `main`）

---

## Task 7: 真机闭环验证（国内 demo 命脉）

**Files:** 无（运行时验证）

- [ ] **Step 1: 启动整套 stack**

Run（在 token-platform 工作树）:
```
cd /d C:\Users\王曙辉\ZCodeProject\token-platform
docker compose up -d --force-recreate sub2api
```
Expected: sub2api 容器用刚 build 的 `sub2api-fork:dev` 起来。

- [ ] **Step 2: 健康检查 + 打开后台**

Run:
```
curl.exe -s http://127.0.0.1:8080/health
```
Expected: 200。浏览器开 `http://127.0.0.1:8080`，登录（admin@sub2api.local）。

- [ ] **Step 3: 准备一个 key，打开「使用 API 密钥」弹窗**

在后台创建/选用一个 anthropic 平台的 key，点「使用 API 密钥」。
Expected: 弹窗出现，SkillMarketSelector 区域加载出 12 个 skill（**验证坑 4 jsDelivr 生效**）。若加载失败显示 loadFailed，开浏览器控制台看 fetch 报错（CORS/网络），回查 Task 2 Step 7 的 CDN 可达性。

- [ ] **Step 4: 勾选一个 skill，验证脚本生成**

勾选 `markitdown`，切到 Terminal(unix) tab。
Expected: 出现第 3 个代码块 `Install Claude Code skills (Bash)`，内容含 `curl`、`sha256sum`、`unzip`（**无 python**）、目标 `$HOME/.claude/skills/markitdown`。

- [ ] **Step 5: 干净环境执行脚本，验证 skill 落地**

在另一台 unix 机器（或 WSL/容器）执行复制的脚本。
Expected: 退出码 0，`~/.claude/skills/markitdown/SKILL.md` 存在且内容完整，sha256 校验通过（脚本内自带校验，失败会 exit 1）。

- [ ] **Step 6: 回归验证——不勾选 skill 时输出与上游一致**

刷新弹窗，不勾任何 skill，看 Terminal + settings.json 两个代码块。
Expected: 与改造前/上游完全一致（无安装脚本块出现）。这正是 Task 5 Step 2 baseline 断言的真机对应。

- [ ] **Step 7: Codex 平台重复一遍**

换一个 openai 平台的 key，打开弹窗，勾选 skill，切 unix tab。
Expected: 出现 `Install Codex package (Bash)`，同时含写 config.toml/auth.json 和 unzip 装 skill。

- [ ] **Step 8: 记录 demo 流程**

把 Step 3-7 的操作顺序整理成一份 3 分钟 demo 脚本（文字 + 截图位置），存到 `state-of-art-skills/docs/` 下，作为大赛演示材料。

---

## Self-Review

**1. Spec coverage:**
- 坑 1（两边没提交）→ Task 2（skill 仓库）+ Task 6（fork）✅
- 坑 2（python 依赖）→ Task 4 + Task 5 Step2 的 `not.toContain('python')` 回归保护 ✅
- 坑 3（缺回归测试）→ Task 5 ✅
- 坑 4（registry CDN）→ Task 3 + Task 2 Step7 验证 + Task 7 Step3 真机验证 ✅
- 真机闭环验证 → Task 7 ✅
- 非目标（Release/Phase1.5）正确排除 ✅

**2. Placeholder scan:** 无 TBD/TODO；每步都有具体命令、代码、预期输出。`<当前分支>` 是真实变量需执行时确认，属正常。✅

**3. Type consistency:** `SkillInstallSelection` 接口（id/name/archiveUrl/sha256/installTarget）在 spec、Task 5 fixture、connectorTemplates.ts 一致；`defaultClaudeOptions()/defaultCodexOptions()` 签名沿用 codex 已有；测试 fixture 字段名与接口完全对应。✅

无问题，计划可执行。
