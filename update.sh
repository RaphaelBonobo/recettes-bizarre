#!/bin/bash
# Met à jour le site depuis le vault et pousse vers GitHub.
set -e
python3 generate.py
git add build/index.html
git commit -m "recettes: $(date '+%Y-%m-%d')"
git push
echo "✓ Vercel déploie automatiquement — site à jour dans ~30s"
