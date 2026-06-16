# Phase 2 (Skill Market) 收尾设计 —— 接入闭环上线

> 日期: 2026-06-16
> 范围: 把已写好但未上线/未验证的 Skill Market 接入闭环打通，达到可演示状态。
> 背靠仓库: `2508756189/state-of-art-skills`（能力仓库）+ `2508756189/sub2api`（fork，连接器）。

---

## 1. 背景与现状

### 1.1 整体打法
组件化智能应用接入的三仓库闭环：

```
sub2api(fork)  ──连接器弹窗──►  拉取 registry ──►  state-of-art-skills(能力仓库)
   ↑ 接入网关 + 可勾选配置              index.json(12 个 skill + zip + sha256)
   └─ Phase 1 已完成
token-platform = Docker 编排 + 文档
```

叙事（面向黑马大赛）: 发一个 key → 弹窗勾选能力包 → 生成带校验的安装脚本 → 一条命令装配好 → 立刻可用。

### 1.2 codex 已完成的产出（本设计的前提，不重做）
经核实，接入闭环的主体代码已写完，但**全部停在本地工作区，从未提交/推送/构建/验证**：

**skill 仓库（`state-of-art-skills`，未跟踪 `??`）：**
- `market/schema.v1.json` — registry JSON Schema
- `market/categories.json` — 5 个分类 + 12 skill 的元数据
- `market/index.json` — 构建产物（含每个 skill 的 zip path / sha256 / size）
- `scripts/build_market.py` — 扫描 `skills/*/SKILL.md` → 打 zip → 算 sha256 → 生成 index.json
- `scripts/test_build_market.py` — 3 个单测（构建/重名/泄密检测）
- `.github/workflows/validate-market.yml` — CI: 测试 + 构建 + `git diff --exit-code` 校验产物最新
- `dist/skills/*.zip` — 12 个打包好的 skill 压缩包

**fork（`sub2api`，工作区 `M`/`??`）：**
- `src/api/skillMarket.ts` — fetch registry + URL 解析 + `toSkillInstallSelection`
- `src/components/keys/SkillMarketSelector.vue` — 搜索/分类/勾选 UI
- `src/components/keys/connectorTemplates.ts` — 已含 `selectedSkills` 字段 + Bash/PowerShell 安装脚本生成器
- `src/components/keys/UseKeyModal.vue` — 已挂载 `<SkillMarketSelector>` + 第 486/495 行把 `selectedSkills` 传进 build 函数 → **闭环已接通**

### 1.3 四个必须填的坑（风险从高到低）

| # | 坑 | 严重度 | 说明 |
|---|---|---|---|
| 1 | 两边代码都没提交 | **致命** | skill 仓库 registry URL 指向 main 分支 raw，但 main 上没有 `market/index.json` → 404；fork 没提交 → 构建不出带 skill market 的镜像。闭环物理上是断的。 |
| 2 | 安装脚本依赖 `python` 解压 | **高** | `connectorTemplates.ts` 的 unix 安装脚本用 `python - <<PY` 解 zip。很多机器 `python` 不存在（只有 `python3`），Codex 用户尤其不保证装 Python。国内 demo 现场会翻车。 |
| 3 | 缺 skill 安装脚本的回归测试 | **中** | `connectorTemplates.spec.ts` 现有 10 个断言**不含任何 skill 相关测试**。Phase 1 的回归基线（空选项 == 上游原版）目前只覆盖到模型/插件，skill 安装脚本的生成是裸奔的。 |
| 4 | registry URL 写死 raw.githubusercontent，国内不稳 | **中** | 浏览器 fetch + raw 在国内不稳定；跨域/CDN 缓存也有风险。国内现场演示需做防御。 |

---

## 2. 目标与非目标

### 2.1 目标（本 spec 范围）
1. 闭环物理上线：两个仓库的 skill 相关改动提交 push，main 分支可访问。
2. 填坑 2：安装脚本不依赖 python。
3. 填坑 3：补 skill 安装脚本的回归测试，锁定输出。
4. 填坑 4：registry 加国内可访问的源，默认安全。
5. 真机走通完整闭环并产出可复用的 demo 流程。

### 2.2 非目标（本 spec 不做，留后续）
- Release 流程 / 一键 `curl|bash` 安装器（Step 3，demo 后）
- Phase 1.5（group 可用模型喂进下拉）
- 新增 skill / 新能力（维持现有 12 个）
- 任何后端服务（skill 仍是纯文件，无后端）

---

## 3. 设计

### 3.1 坑 1 修复 —— 闭环上线

**skill 仓库提交策略：**
- 提交 `market/ scripts/ .github/ dist/skills/*.zip`，以及 `.gitignore`（含 `!dist/skills/*.zip` 负向豁免）和 README。
- 保留 CI 的 `git diff --exit-code` 校验：改 skill 后必须重新跑 `build_market.py` 并把更新后的 `index.json` + zip 一起提交。这是**可复现、可审计**的正确做法，不改。
- 提交前本地跑一遍 `python scripts/build_market.py` 确认 `git status` 干净（产物已最新）。

**fork 提交策略（严格遵循 token-platform dev plan §3 改动收敛原则）：**
- 新增文件：`src/api/skillMarket.ts`、`src/api/__tests__/skillMarket.spec.ts`、`src/components/keys/SkillMarketSelector.vue`
- 修改文件（仅最小挂载点 + 追加 i18n）：`UseKeyModal.vue`（2 处：挂载组件 + selectedSkills 传入）、`connectorTemplates.ts`、`connectorPresets.ts`、`ConnectorOptions.vue`、`KeysView.vue`、`zh.ts`、`en.ts`
- 一次提交，commit message 体现 `feat(keys): skill market integration`
- 提交后 `docker build -t sub2api-fork:dev` 重建镜像

### 3.2 坑 2 修复 —— 去掉 python 依赖

`connectorTemplates.ts` 两处 unix 安装脚本（`buildClaudeSkillInstallScript`、`buildCodexInstallScript`）的解压段：

**现状（依赖 python）：**
```bash
python - "$zip_path" "$(dirname "$target")" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as zf:
    zf.extractall(sys.argv[2])
PY
```

**改为（依赖 unzip，所有 Linux/macOS 基本自带）：**
```bash
unzip -o -q "$zip_path" -d "$(dirname "$target")"
```

`unzip` 在 Debian/Ubuntu（默认装）/ macOS（自带）/ 绝大多数 Linux 发行版都存在。Windows 走 PowerShell 的 `Expand-Archive`，不受影响（已是现状）。

PowerShell 版本不动（已用 `Expand-Archive`，无 python 依赖）。

### 3.3 坑 3 修复 —— 补 skill 安装脚本回归测试

在 `connectorTemplates.spec.ts` 新增 describe 块，覆盖：

1. **Claude + 选中 1 个 skill + unix**：生成的第 3 个 FileConfig 是 Bash 安装脚本，包含 `curl ... archiveUrl`、`sha256sum`、`unzip`、目标路径 `$HOME/.claude/skills/<id>`。
2. **Claude + 选中 skill + powershell**：是 PowerShell 脚本，含 `Invoke-WebRequest`、`Get-FileHash`、`Expand-Archive`。
3. **Codex + 选中 skill + unix**：安装脚本同时写入 config.toml/auth.json **并** 安装 skill（两个职责合一）。
4. **回归基线保护**：`selectedSkills: []`（默认）时，`buildAnthropicFiles` 和 `buildCodexFiles` 的输出**与现状/上游完全一致，不出现安装脚本块** —— 锁定"不勾选 skill 不改变 baseline"。

断言用具体 fixture（固定 archiveUrl/sha256/installTarget），不依赖网络。

### 3.4 坑 4 修复 —— registry 源

**默认 URL 改为 jsDelivr CDN（国内可达、有 CORS、带 CDN 缓存）：**
```
https://cdn.jsdelivr.net/gh/2508756189/state-of-art-skills@main/market/index.json
```

`api/skillMarket.ts` 的 `DEFAULT_SKILL_MARKET_REGISTRY_URL` 改这个。archive URL 解析 `resolveSkillArchiveUrl` 已能正确处理相对路径（jsDelivr 同样按仓库路径映射），无需改逻辑。

**为什么 jsDelivr：** 国内可直连、支持 CORS（fetch 无跨域问题）、有全球 CDN。raw.githubusercontent 作为备选（代码里已是正确 fallback 思路，保留）。

**可选增强（不阻塞上线）：** 在 sub2api 后台/设置里暴露 registry URL 为可配置项，演示时可现场切。本 spec 先只改默认值，配置化留 Step 3。

### 3.5 验证闭环（真机）

重建镜像后：
1. `docker compose up -d`，开 8080 后台
2. 准备一个 key（platform=anthropic 或 openai）
3. 打开「使用 API 密钥」弹窗 → 看到 SkillMarketSelector 加载出 12 个 skill（验证坑 4 的 CDN 生效）
4. 勾选 1 个 skill（如 `markitdown`）→ 终端 tab 出现安装脚本块
5. 复制脚本到**干净环境**（另一台机或容器）执行 → 验证 `~/.claude/skills/markitdown/` 存在、SKILL.md 完整、sha256 校验通过
6. 未勾选任何 skill 时，输出与上游原版一致（回归基线）

---

## 4. 架构与数据流（确认无变化）

```
[Sub2API fork 后台 8080]
  UseKeyModal.vue
    ├─ <SkillMarketSelector v-model="selectedSkills" :runtime>
    │     └─ loadSkillRegistry()  ──fetch(jsDelivr CDN)──►  market/index.json
    │                                                            └─ archive.path → dist/skills/<id>.zip
    └─ currentFiles = buildAnthropicFiles/buildCodexFiles({ ..., selectedSkills })
          └─ 生成: Terminal/env 块 + settings.json/config.toml + 【安装脚本(Bash/PS, 含 sha256 校验)】
                              │
                              ▼  用户复制执行
                    curl zip → sha256 校验 → unzip → ~/.claude|codex/skills/<id>/
```

无后端、无新组件、无新接口。改动全部收敛在 codex 已搭好的架子内。

---

## 5. 受影响文件清单

**state-of-art-skills（新增提交）：**
- `market/schema.v1.json`、`market/categories.json`、`market/index.json`
- `scripts/build_market.py`、`scripts/test_build_market.py`
- `.github/workflows/validate-market.yml`
- `dist/skills/*.zip`（12 个）
- `.gitignore`、`README.md`（更新说明）

**sub2api fork（提交工作区改动 + 修复）：**
- 新增: `src/api/skillMarket.ts`、`src/api/__tests__/skillMarket.spec.ts`、`src/components/keys/SkillMarketSelector.vue`
- 修改（已有改动）: `UseKeyModal.vue`、`connectorTemplates.ts`、`connectorPresets.ts`、`ConnectorOptions.vue`、`KeysView.vue`、`zh.ts`、`en.ts`
- **本 spec 新增修改**: `connectorTemplates.ts`（坑 2：python→unzip）、`connectorTemplates.spec.ts`（坑 3：补 skill 测试）、`skillMarket.ts`（坑 4：默认 URL 改 jsDelivr）

---

## 6. 验证清单

- [ ] skill 仓库: `python scripts/build_market.py` 后 `git status` 干净
- [ ] skill 仓库: `python scripts/test_build_market.py` 全绿
- [ ] skill 仓库: push 后 `https://cdn.jsdelivr.net/gh/2508756189/state-of-art-skills@main/market/index.json` 可访问
- [ ] fork: `pnpm test` 全绿（含新增 skill 安装脚本断言 + 回归基线）
- [ ] fork: `pnpm build` 通过
- [ ] fork: `docker build -t sub2api-fork:dev` 成功
- [ ] 真机: 弹窗加载出 12 个 skill（CDN 生效）
- [ ] 真机: 勾选 skill → 脚本含 unzip（无 python）→ 干净环境执行成功 + sha256 通过
- [ ] 真机: 不勾选 skill → 输出与上游一致（无回归）

---

## 7. 后续（Step 3，本 spec 之后）

- Release 流程：tag → 自动打全量 zip + index 挂 GitHub Release assets，支持 `curl install.sh | bash`
- registry URL 在后台可配置
- Phase 1.5：group 可用模型喂进弹窗下拉
- 大赛技术材料：三仓库关系图 + 3 分钟 demo 脚本
