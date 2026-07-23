const { Notice, Plugin } = require("obsidian");

const REMOTE_PLUGIN_ID = "remote-ssh";
const COMMAND = "~/.local/bin/obsidian-relevant-tree";
const PAYLOAD_SCHEMA = "obsidian.relevant-tree.v2";
const CACHE_SCHEMA = "remote-relevant-tree.cache.v1";
const CHUNK_SIZE = 200;
const VISIBLE_DOT_FOLDERS = new Set([".agents", ".pi", ".agents-global", ".pi-global"]);

function shellQuote(value) {
  return `'${String(value).replaceAll("'", `'"'"'`)}'`;
}

function validPath(path) {
  return typeof path === "string" && path.length > 0 && !path.startsWith("/") &&
    path.split("/").every((part) => part && part !== "." && part !== ".." &&
      (!part.startsWith(".") || VISIBLE_DOT_FOLDERS.has(part)));
}

function validatePayload(raw, root) {
  if (!raw || raw.schema !== PAYLOAD_SCHEMA || raw.complete !== true || raw.root !== root ||
      !Array.isArray(raw.entries)) {
    throw new Error("invalid or incomplete scanner response");
  }

  const seen = new Set();
  const entries = raw.entries.map((entry) => {
    if (!entry || !validPath(entry.path) || !["file", "folder"].includes(entry.type) ||
        seen.has(entry.path)) {
      throw new Error(`invalid scanner entry: ${entry?.path ?? "(missing path)"}`);
    }
    seen.add(entry.path);
    const values = [entry.ctime, entry.mtime, entry.size];
    if (!values.every((value) => Number.isFinite(value) && value >= 0)) {
      throw new Error(`invalid stat for ${entry.path}`);
    }
    return {
      path: entry.path,
      type: entry.type,
      ctime: Math.trunc(entry.ctime),
      mtime: Math.trunc(entry.mtime),
      size: Math.trunc(entry.size),
    };
  });

  const types = new Map(entries.map((entry) => [entry.path, entry.type]));
  for (const entry of entries) {
    const slash = entry.path.lastIndexOf("/");
    if (slash >= 0 && types.get(entry.path.slice(0, slash)) !== "folder") {
      throw new Error(`missing folder ancestor for ${entry.path}`);
    }
  }

  return {
    schema: PAYLOAD_SCHEMA,
    complete: true,
    root,
    entries,
    matching_files: entries.filter((entry) => entry.type === "file").length,
    scanned_directories: Number.isFinite(raw.scanned_directories) ? raw.scanned_directories : 0,
  };
}

function sameIdentity(a, b) {
  return !!a && !!b && a.profile === b.profile && a.root === b.root &&
    a.remoteVersion === b.remoteVersion && a.host === b.host && a.port === b.port &&
    a.username === b.username;
}

function ordered(entries, reverse = false) {
  return [...entries].sort((a, b) => {
    const depth = a.path.split("/").length - b.path.split("/").length;
    if (depth) return reverse ? -depth : depth;
    if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
    return a.path.localeCompare(b.path);
  });
}

function isFolder(file) {
  return !!file && Array.isArray(file.children);
}

function toRemoteEntry(entry) {
  return { ...entry, isDirectory: entry.type === "folder" };
}

function makeBuilder(loader) {
  const builder = loader.makeBuilder();
  // The local Remote SSH compatibility build defaults to Markdown-only.
  if (builder.options) builder.options.markdownOnly = false;
  return builder;
}

function idleYield() {
  if (typeof window.requestIdleCallback === "function") {
    return new Promise((resolve) => window.requestIdleCallback(resolve, { timeout: 500 }));
  }
  return new Promise((resolve) => window.setTimeout(resolve, 0));
}

class RemoteRelevantTree extends Plugin {
  async onload() {
    this.runningLoader = null;
    this.completedLoader = null;
    this.restoredLoaders = new WeakSet();
    this.failures = new WeakMap();
    this.cache = await this.loadData().catch(() => null);
    this.unloaded = false;
    this.state = { text: "Remote tree: waiting for Remote SSH", detail: "Waiting for the remote adapter." };

    this.statusEl = this.addStatusBarItem();
    this.statusEl.addClass("mod-clickable");
    this.registerDomEvent(this.statusEl, "click", () => new Notice(this.state.detail, 7000));
    this.setStatus(this.state.text, this.state.detail);

    this.app.workspace.onLayoutReady(() => {
      void this.tryLoad();
      this.registerInterval(window.setInterval(() => void this.tryLoad(), 1500));
    });
  }

  onunload() {
    this.unloaded = true;
  }

  setStatus(text, detail = text) {
    this.state = { text, detail };
    this.statusEl?.setText(text);
    if (this.statusEl) this.statusEl.title = detail;
  }

  getRemoteContext() {
    const remote = this.app.plugins?.plugins?.[REMOTE_PLUGIN_ID];
    const client = remote?.conn?.client;
    const root = remote?.conn?.activeRemoteBasePath;
    const loader = remote?.lazyLoader;
    if (!client || !root || !loader?.makeBuilder || !loader?.markLoaded || !remote.conn.isAlive?.()) {
      return null;
    }
    const profile = remote.settings?.activeProfileId || remote.settings?.autoConnectProfileId || "unknown";
    const endpoint = remote.conn.activeProfile || remote.settings?.profiles?.find((item) => item.id === profile) || {};
    return {
      remote,
      client,
      root,
      loader,
      identity: {
        profile,
        root,
        remoteVersion: remote.manifest?.version || "unknown",
        host: endpoint.host || "unknown",
        port: endpoint.port || 22,
        username: endpoint.username || endpoint.user || "unknown",
      },
    };
  }

  isCurrent(context) {
    const current = this.getRemoteContext();
    return !this.unloaded && current?.client === context.client && current.loader === context.loader &&
      sameIdentity(current.identity, context.identity);
  }

  async buildEntries(context, entries, label) {
    const list = ordered(entries);
    const builder = makeBuilder(context.loader);
    let processed = 0;
    for (let index = 0; index < list.length; index += CHUNK_SIZE) {
      if (!this.isCurrent(context)) throw new Error("remote connection changed during load");
      const chunk = list.slice(index, index + CHUNK_SIZE).map(toRemoteEntry);
      const result = await builder.buildChunked(chunk, CHUNK_SIZE);
      if (result.errors?.length) throw new Error(`${result.errors.length} model build errors`);
      for (const entry of list.slice(index, index + CHUNK_SIZE)) {
        if (!this.app.vault.getAbstractFileByPath(entry.path)) {
          throw new Error(`model builder omitted ${entry.path}`);
        }
      }
      processed += chunk.length;
      this.setStatus(
        `Remote tree: ${label} ${processed}/${list.length}`,
        `${label}: ${processed} of ${list.length} cached tree entries processed.`,
      );
      await idleYield();
    }
    if (!this.isCurrent(context)) throw new Error("remote connection changed after load");
    context.loader.markLoaded("");
    for (const entry of list) {
      if (entry.type === "folder") context.loader.markLoaded(entry.path);
    }
  }

  async reconcile(context, previous, fresh) {
    const builder = makeBuilder(context.loader);
    const freshByPath = new Map(fresh.entries.map((entry) => [entry.path, entry]));
    const previousEntries = previous?.entries || [];
    const removals = previousEntries.filter((entry) => {
      const next = freshByPath.get(entry.path);
      return !next || next.type !== entry.type;
    });

    for (const entry of ordered(removals, true)) {
      if (!this.isCurrent(context)) throw new Error("remote connection changed during refresh");
      builder.removeOne(entry.path);
      if (entry.type === "folder") context.loader.loaded?.delete?.(entry.path);
    }

    for (const entry of fresh.entries) {
      const existing = this.app.vault.getAbstractFileByPath(entry.path);
      if (existing && isFolder(existing) !== (entry.type === "folder")) {
        builder.removeOne(entry.path);
      }
    }

    await this.buildEntries(context, fresh.entries, "indexing");

    if (!this.isCurrent(context)) throw new Error("remote connection changed before stat refresh");
    let changed = 0;
    for (const entry of fresh.entries) {
      if (entry.type !== "file") continue;
      const file = this.app.vault.getAbstractFileByPath(entry.path);
      if (!file || isFolder(file)) continue;
      const stat = file.stat || {};
      if ((stat.mtime !== entry.mtime || stat.size !== entry.size) &&
          (!stat.mtime || entry.mtime >= stat.mtime)) {
        builder.modifyOne(entry.path, { ctime: entry.ctime, mtime: entry.mtime, size: entry.size });
        changed += 1;
      }
    }
    return { removed: removals.length, changed };
  }

  async tryLoad() {
    const context = this.getRemoteContext();
    if (!context) return;
    const { client, root, loader, identity } = context;
    if (this.runningLoader === loader || this.completedLoader === loader) return;
    if ((this.failures.get(loader) || 0) >= 3) return;

    this.runningLoader = loader;
    let restored = false;
    try {
      this.setStatus("Remote tree: checking remote…", "Scanning the relevant remote tree.");
      const scanPromise = client.exec(`${COMMAND} --root ${shellQuote(root)}`);

      let previous = null;
      if (this.cache?.schema === CACHE_SCHEMA && sameIdentity(this.cache.identity, identity)) {
        try {
          previous = validatePayload(this.cache.payload, root);
          if (!this.restoredLoaders.has(loader)) {
            await this.buildEntries(context, previous.entries, "restoring cache");
            this.restoredLoaders.add(loader);
          }
          restored = true;
          this.setStatus(
            `Remote tree: cache ready (${previous.matching_files} files)`,
            `Cached tree restored: ${previous.matching_files} files. Checking remote changes…`,
          );
        } catch (error) {
          console.warn("Remote Relevant Tree cache ignored", error);
          previous = null;
        }
      }

      const result = await scanPromise;
      if (result.exitCode !== 0) {
        throw new Error(result.stderr.trim() || `scanner exited ${result.exitCode}`);
      }
      const fresh = validatePayload(JSON.parse(result.stdout), root);
      if (!this.isCurrent(context)) throw new Error("remote connection changed after scan");
      const delta = await this.reconcile(context, previous, fresh);
      if (!this.isCurrent(context)) throw new Error("remote connection changed before cache save");

      this.cache = { schema: CACHE_SCHEMA, identity, payload: fresh };
      try {
        await this.saveData(this.cache);
      } catch (error) {
        console.warn("Remote Relevant Tree cache save failed", error);
      }

      if (!this.isCurrent(context)) throw new Error("remote connection changed after cache save");
      this.completedLoader = loader;
      this.failures.delete(loader);
      const detail = `Tree ready: ${fresh.matching_files} relevant files, ` +
        `${fresh.entries.length - fresh.matching_files} folders; ${delta.changed} changed, ` +
        `${delta.removed} removed. Obsidian metadata may continue resolving briefly.`;
      this.setStatus(`Remote tree: ready (${fresh.matching_files} files)`, detail);
      console.info(`Remote Relevant Tree: ${detail}`);
      new Notice(`Remote tree ready: ${fresh.matching_files} relevant files`);
    } catch (error) {
      const failures = (this.failures.get(loader) || 0) + 1;
      this.failures.set(loader, failures);
      console.error(`Remote Relevant Tree attempt ${failures}/3 failed`, error);
      this.cache = {
        ...(this.cache || {}),
        lastError: String(error?.message || error),
        lastErrorAt: new Date().toISOString(),
      };
      try { await this.saveData(this.cache); } catch {}
      this.setStatus(
        restored
          ? `Remote tree: cache ready · refresh failed (${failures}/3)`
          : `Remote tree: load failed (${failures}/3)`,
        `${restored ? "Cached tree is available, but refresh" : "Tree load"} failed: ${error.message || error}`,
      );
      if (failures === 3) new Notice("Remote Relevant Tree failed; click its status or see Developer Console");
    } finally {
      if (this.runningLoader === loader) this.runningLoader = null;
    }
  }
}

module.exports = RemoteRelevantTree;
module.exports.__test = { makeBuilder, ordered, sameIdentity, shellQuote, validPath, validatePayload };
