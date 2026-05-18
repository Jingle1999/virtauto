# virtauto site MVP

## How to deploy
1. Copy the `site/` folder and `.github/workflows/` into your repo root.
2. Commit & push to `main`.
3. In GitHub → Settings → Pages, ensure **Build & deployment = GitHub Actions**.
4. Open the latest deployment from the Actions tab and click **View deployment**.

## Commit commands
```bash
git checkout -b make-site-visible || git checkout make-site-visible
git add site .github/workflows
git commit -m "feat(website): minimal visible site + pages deploy workflow"
git push -u origin make-site-visible
git checkout main && git merge --no-ff make-site-visible -m "Merge: minimal visible site" && git push
```
