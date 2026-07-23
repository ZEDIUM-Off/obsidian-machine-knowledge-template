# Politique de publication

Ce dépôt est public par conception. Toute nouvelle donnée est refusée par défaut.

## Ne jamais versionner

- `.obsidian/user/**`, `workspace*.json`, récents, caches, logs et récupération de fichiers ;
- `remote-ssh`, profils d'agents, sessions et fichiers de credentials ;
- `plugins/*/{main.js,styles.css,manifest.json}` ou thèmes téléchargés ;
- clés, jetons, cookies, adresses privées, hostnames, noms d'utilisateur, emails et chemins absolus ;
- notes ou captures provenant directement d'une machine réelle sans revue humaine.

## Avant publication

```bash
python3 scripts/check_public.py
git diff --cached
# Optionnel : gitleaks dir .
```

Toute extension de la liste blanche de `scripts/check_public.py` exige une revue manuelle. Un secret publié doit être révoqué : le supprimer d'un commit ne suffit pas.
