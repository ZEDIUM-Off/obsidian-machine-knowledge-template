# Publication policy

The repository publishes structure, specifications, visual configuration and reviewed tools only.

## Never version

- `.obsidian/user/**`, workspace/recent state, caches, logs or recovery data;
- credentials, sessions, remote profiles or agent transcripts;
- downloaded third-party plugin/theme binaries;
- machine inventories or project content copied without review.

The bundled `remote-relevant-tree` source is the explicit exception: it is maintained with its MIT license and self-test.

## Before push

```bash
python3 scripts/check_public.py
python3 -m unittest scripts/test_sync_visuals.py
python3 -m unittest tools/kb/test_kb.py
python3 scripts/sync_visuals.py --check
git diff --cached
```
