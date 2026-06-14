const fs = require("fs");
const path = require("path");
const { ClassicLevel } = require("classic-level");

const home = process.env.USERPROFILE || process.env.HOME;
const claude3p = path.join(home, "AppData", "Local", "Claude-3p");
const leveldbPath = path.join(claude3p, "Local Storage", "leveldb");
const sessionRoot = path.join(claude3p, "claude-code-sessions");

const BASE = "D:\\\u7535\u52a8\u8f66\u5145\u7535\u5bf9\u63a5\u6587\u6863";
const projects = [
  {
    cwd: `${BASE}\\\u7518\u5b5ccpw\u8df3\u677f\u63a5\u4e3b\u5e73\u53f0\u9879\u76ee`,
    groupId: "cg-fz-cpw-jump-main",
    name: "\u4e30\u6cfd-cpw\u8df3\u677f\u4e3b\u5e73\u53f0\u6a21\u5f0f",
  },
  {
    cwd: `${BASE}\\\u4e3b\u5e73\u53f0\u76f4\u8fde\u6a21\u5f0f`,
    groupId: "cg-hr-main-direct",
    name: "\u534e\u6995-\u4e3b\u5e73\u53f0\u76f4\u8fde\u6a21\u5f0f",
  },
];

function normalizePath(value) {
  return String(value || "")
    .replace(/^\\\\\?\\/, "")
    .replace(/[\\/]+$/, "")
    .toLowerCase();
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function findSessionDir(root) {
  const candidates = [];
  for (const account of fs.readdirSync(root, { withFileTypes: true })) {
    if (!account.isDirectory()) continue;
    const accountPath = path.join(root, account.name);
    for (const org of fs.readdirSync(accountPath, { withFileTypes: true })) {
      if (org.isDirectory()) candidates.push(path.join(accountPath, org.name));
    }
  }
  candidates.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  return candidates[0];
}

function collectAssignments() {
  const sessionDir = findSessionDir(sessionRoot);
  if (!sessionDir) throw new Error(`Claude session dir not found under ${sessionRoot}`);

  const byCwd = new Map(projects.map((project) => [normalizePath(project.cwd), project]));
  const assignments = {};
  const order = Object.fromEntries(projects.map((project) => [project.groupId, []]));
  const sortable = Object.fromEntries(projects.map((project) => [project.groupId, []]));

  for (const name of fs.readdirSync(sessionDir)) {
    if (!/^local_.*\.json$/.test(name)) continue;
    const file = path.join(sessionDir, name);
    let obj;
    try {
      obj = readJson(file);
    } catch {
      continue;
    }

    const project = byCwd.get(normalizePath(obj.cwd || obj.originCwd));
    if (!project) continue;
    const sessionId = obj.sessionId || path.basename(name, ".json");
    assignments[sessionId] = project.groupId;
    if (obj.cliSessionId) assignments[obj.cliSessionId] = project.groupId;
    sortable[project.groupId].push({
      sessionId,
      cliSessionId: obj.cliSessionId,
      lastActivityAt: Number(obj.lastActivityAt || obj.lastFocusedAt || obj.createdAt || 0),
    });
  }

  for (const project of projects) {
    order[project.groupId] = sortable[project.groupId]
      .sort((a, b) => b.lastActivityAt - a.lastActivityAt || a.sessionId.localeCompare(b.sessionId))
      .map((item) => item.sessionId);
  }
  return { assignments, order };
}

function parseChromiumValue(raw) {
  const text = String(raw || "");
  const prefix = text.startsWith("\x01") ? "\x01" : "";
  const body = prefix ? text.slice(1) : text;
  return { prefix, value: body ? JSON.parse(body) : {} };
}

function stringifyChromiumValue(prefix, value) {
  const json = JSON.stringify(value).replace(/[^\x00-\x7F]/g, (char) => {
    const code = char.codePointAt(0);
    if (code <= 0xFFFF) return `\\u${code.toString(16).padStart(4, "0")}`;
    const high = Math.floor((code - 0x10000) / 0x400) + 0xD800;
    const low = ((code - 0x10000) % 0x400) + 0xDC00;
    return `\\u${high.toString(16).padStart(4, "0")}\\u${low.toString(16).padStart(4, "0")}`;
  });
  return `${prefix || "\x01"}${json}`;
}

async function getKey(db, suffix) {
  for await (const [key] of db.iterator()) {
    if (String(key).endsWith(suffix)) return key;
  }
  return `_app://localhost\x00\x01${suffix}`;
}

async function main() {
  const { assignments, order } = collectAssignments();
  const db = new ClassicLevel(leveldbPath, { keyEncoding: "utf8", valueEncoding: "utf8" });
  await db.open();

  const now = Date.now();
  const groupDefs = projects.map((project) => ({ id: project.groupId, name: project.name }));
  const projectIds = new Set(projects.map((project) => project.groupId));

  const dframeKey = await getKey(db, "dframe-store");
  let dframeRaw = "\x01{}";
  try {
    dframeRaw = await db.get(dframeKey);
  } catch {}
  const dframe = parseChromiumValue(dframeRaw);
  dframe.value.state = dframe.value.state || {};
  const state = dframe.value.state;
  state.lastKnownMode = "code";
  state.groupByByMode = { ...(state.groupByByMode || {}), code: "custom" };
  state.customGroups = [
    ...(state.customGroups || []).filter((group) => !projectIds.has(group.id)),
    ...groupDefs,
  ];
  state.customGroupAssignments = { ...(state.customGroupAssignments || {}), ...assignments };
  state.customGroupOrder = { ...(state.customGroupOrder || {}), ...order };
  state.collapsedGroups = (state.collapsedGroups || []).filter((id) => !projectIds.has(id));
  if (dframe.value.version === undefined) dframe.value.version = 0;
  await db.put(dframeKey, stringifyChromiumValue(dframe.prefix, dframe.value));

  const sliceKey = await getKey(db, "LSS-persisted.dframe-local-slice");
  let sliceRaw = "\x01{}";
  try {
    sliceRaw = await db.get(sliceKey);
  } catch {}
  const slice = parseChromiumValue(sliceRaw);
  slice.value.value = slice.value.value || {};
  slice.value.value.pinnedOrder = slice.value.value.pinnedOrder || [];
  slice.value.value.customGroupAssignments = {
    ...(slice.value.value.customGroupAssignments || {}),
    ...assignments,
  };
  slice.value.value.customGroupOrder = { ...(slice.value.value.customGroupOrder || {}), ...order };
  slice.value.tabId = slice.value.tabId || "codex-import";
  slice.value.timestamp = now;
  await db.put(sliceKey, stringifyChromiumValue(slice.prefix, slice.value));

  await db.close();
  console.log(
    JSON.stringify(
      {
        ok: true,
        dframeKey,
        sliceKey,
        assignedSessions: Object.keys(assignments).length,
        groups: groupDefs.map((group) => ({ ...group, count: order[group.id].length })),
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
