# Cell 3 — Install all Verdant packages + dependencies
%%bash
set -e
cd /content/Verdant-Minds
python -V
pip -V
pip install -U pip setuptools wheel
pip install -e ./ethomorphic
pip install -e ./verdant_v2
pip install -e ./cultivation
pip install -U numpy scipy scikit-learn networkx matplotlib
echo "Installation complete."
