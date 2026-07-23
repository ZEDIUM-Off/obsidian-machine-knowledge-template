# Remote Relevant Tree provenance

- Version: `0.3.1`
- Runtime source: `main.js` (unminified CommonJS; no separate build step)
- License: MIT, see `LICENSE`
- Companion scanner: `tools/bin/obsidian-relevant-tree`
- Compatibility target: Obsidian desktop and Remote SSH `1.1.7`

Verification:

```bash
node .obsidian/plugins/remote-relevant-tree/self-test.js
tools/bin/obsidian-relevant-tree --self-test
```

The plugin admits only `.agents`, `.pi`, `.agents-global` and `.pi-global` among dot-directories. `.pi-subagents` is deliberately excluded.
