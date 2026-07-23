# Vault tools

`obsidian-relevant-tree` exposes supported Markdown, Canvas, Base and media files to Remote SSH while admitting only `.agents`, `.pi`, `.agents-global` and `.pi-global` among dot-directories.

Install with:

```bash
install -Dm755 tools/bin/obsidian-relevant-tree ~/.local/bin/obsidian-relevant-tree
```

Set `KB_VAULT`, `GLOBAL_AGENTS_PATH` and `GLOBAL_PI_PATH` when their defaults (`~/workspaces`, `~/.agents`, `~/.pi`) differ.
