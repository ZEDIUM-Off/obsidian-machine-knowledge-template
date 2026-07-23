#!/usr/bin/env node
const Module = require("module");
const originalLoad = Module._load;
Module._load = (name, parent, main) => name === "obsidian"
  ? { Notice: class {}, Plugin: class {} }
  : originalLoad(name, parent, main);
global.window = {
  setTimeout,
  requestIdleCallback: (callback) => { callback(); return 1; },
};

const RemoteRelevantTree = require("./main.js");
const { validPath } = RemoteRelevantTree.__test;
if (!validPath("project/.agents/skills/demo/SKILL.md") ||
    !validPath(".pi-global/agent/skills/demo/SKILL.md") ||
    validPath("project/.git/config.md")) {
  throw new Error("selective dot-folder validation failed");
}
const root = "/vault";
const identity = {
  profile: "profile", root, remoteVersion: "1.1.7", host: "server", port: 22, username: "user",
};
const entry = (path, type, mtime = 0, size = 0) => ({ path, type, ctime: mtime, mtime, size });
const cached = {
  schema: "obsidian.relevant-tree.v2", complete: true, root,
  entries: [entry("docs", "folder"), entry("docs/note.md", "file", 1, 1), entry("docs/stale.md", "file", 1, 1)],
};
const fresh = {
  schema: "obsidian.relevant-tree.v2", complete: true, root,
  entries: [
    entry("docs", "folder"), entry("docs/note.md", "file", 2, 2),
    entry("docs/new.md", "file", 1, 1), entry("docs/image.png", "file", 1, 3),
  ],
};
const files = new Map();
const builder = {
  options: { markdownOnly: true },
  async buildChunked(entries) {
    let filesAdded = 0, foldersAdded = 0, skipped = 0;
    for (const item of entries) {
      if (this.options.markdownOnly && !item.isDirectory && !item.path.endsWith(".md")) { skipped++; continue; }
      if (files.has(item.path)) { skipped++; continue; }
      files.set(item.path, item.isDirectory
        ? { path: item.path, children: [] }
        : { path: item.path, stat: { ctime: item.ctime, mtime: item.mtime, size: item.size } });
      item.isDirectory ? foldersAdded++ : filesAdded++;
    }
    return { filesAdded, foldersAdded, skipped, errors: [] };
  },
  removeOne(path) { files.delete(path); },
  modifyOne(path, stat) { files.get(path).stat = stat; },
};
const marked = new Set();
let scans = 0;
const client = {
  exec: async () => { scans++; return { exitCode: 0, stdout: JSON.stringify(fresh), stderr: "" }; },
};
const loader = { makeBuilder: () => builder, markLoaded: (path) => marked.add(path), loaded: new Set() };
const remote = {
  conn: {
    client, activeRemoteBasePath: root, isAlive: () => true,
    activeProfile: { id: "profile", host: "server", port: 22, username: "user" },
  },
  lazyLoader: loader,
  settings: { activeProfileId: "profile" },
  manifest: { version: "1.1.7" },
};

(async () => {
  const plugin = new RemoteRelevantTree();
  plugin.app = {
    plugins: { plugins: { "remote-ssh": remote } },
    vault: { getAbstractFileByPath: (path) => files.get(path) || null },
  };
  plugin.statusEl = { setText() {} };
  plugin.runningLoader = null;
  plugin.completedLoader = null;
  plugin.restoredLoaders = new WeakSet();
  plugin.failures = new WeakMap();
  plugin.cache = { schema: "remote-relevant-tree.cache.v1", identity, payload: cached };
  plugin.unloaded = false;
  plugin.saveData = async (data) => { plugin.saved = data; };

  await plugin.tryLoad();
  if (!files.has("docs/new.md") || !files.has("docs/image.png") || files.has("docs/stale.md")) {
    throw new Error("delta reconciliation failed");
  }
  if (files.get("docs/note.md").stat.mtime !== 2) throw new Error("stat refresh failed");
  if (!marked.has("docs") || plugin.completedLoader !== loader) throw new Error("completion state failed");
  if (builder.options.markdownOnly !== false) throw new Error("Markdown-only builder was not disabled");
  if (plugin.saved?.payload?.entries.length !== 4) throw new Error("cache save failed");

  const reconnectLoader = { ...loader, loaded: new Set() };
  remote.lazyLoader = reconnectLoader;
  await plugin.tryLoad();
  if (scans !== 2 || plugin.completedLoader !== reconnectLoader) throw new Error("same-client reconnect skipped");
  console.log("Remote Relevant Tree self-test: PASS");
})().catch((error) => { console.error(error); process.exitCode = 1; });
