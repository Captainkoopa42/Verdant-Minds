# Cell 2 — Create workspace symlink for editable installs
%%bash
set -e
cd /content
mkdir -p /workspace
ln -sf /content/Verdant-Minds /workspace/Verdant-Minds
echo "Workspace link created:"
ls -l /workspace
