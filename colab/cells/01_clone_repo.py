# Cell 1 — Clone repo and checkout V2
%%bash
set -e
rm -rf Verdant-Minds
git clone https://github.com/Captainkoopa42/Verdant-Minds.git
cd Verdant-Minds
git checkout V2
echo "Repo commit:"
git rev-parse HEAD
