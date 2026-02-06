# QMD Embedding & Sync

## Slow Embedding Over Time

Run embedding at lowest CPU priority (won't affect other work):

```bash
./slow-embed.sh &
```

Or via cron (runs 2 hours each night):
```bash
# Add to crontab -e
0 2 * * * timeout 2h /home/daaronch/semantic-gtm/qmd-sync/slow-embed.sh
```

Progress is saved - you can kill and resume anytime.

## Sharing Embeddings Across Machines

The QMD index is stored at `~/.cache/qmd/index.sqlite` (~200-300MB).

### Option 1: Rsync (Recommended)

**Requirements:** Same directory structure on all machines

```bash
# On source machine (after embedding)
rsync -avz ~/.cache/qmd/index.sqlite user@other-machine:~/.cache/qmd/

# Collections use paths like:
# qmd://expanso-docs/components/inputs/file.md
# → /home/daaronch/docs-expanso-work/docs/components/inputs/file.md
```

**Path consistency:** If paths differ, QMD will still search but `qmd get` will fail.
Use symlinks to normalize paths across machines:
```bash
# On Mac, create matching paths
mkdir -p ~/docs-expanso-work
ln -s /actual/path/to/docs ~/docs-expanso-work/docs
```

### Option 2: Git LFS (For Team Sharing)

```bash
cd ~/aiskills  # or your shared repo
git lfs install
git lfs track "*.sqlite"
cp ~/.cache/qmd/index.sqlite ./qmd/
git add qmd/index.sqlite
git commit -m "Add QMD embeddings"
git push
```

Then on other machines:
```bash
git pull
cp qmd/index.sqlite ~/.cache/qmd/
```

### Option 3: Cloud Storage

```bash
# Upload after embedding
aws s3 cp ~/.cache/qmd/index.sqlite s3://your-bucket/qmd/index.sqlite

# Download on other machine
aws s3 cp s3://your-bucket/qmd/index.sqlite ~/.cache/qmd/
```

## What Gets Shared

| File | Size | Contains | Shareable? |
|------|------|----------|------------|
| `index.sqlite` | ~200MB | Documents + embeddings + FTS index | ✅ Yes |
| `models/` | ~300MB | Embedding model (auto-downloads) | Optional |

## Recommended Setup for Multi-Machine

1. **Primary machine** (fastest CPU): Run `qmd embed`
2. **Sync index.sqlite** to other machines via rsync/S3
3. **Standardize paths** using symlinks
4. **Re-sync weekly** or when collections change significantly

## Checking Status

```bash
qmd status  # Shows files indexed vs embedded
```
