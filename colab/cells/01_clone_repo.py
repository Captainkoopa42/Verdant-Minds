# Cell 1 — Clone repo and use the current branch
%%bash
set -e
rm -rf Verdant-Minds
git clone https://github.com/Captainkoopa42/Verdant-Minds.git
cd Verdant-Minds
git use the current branch
echo "Repo commit:"
git rev-parse HEAD
