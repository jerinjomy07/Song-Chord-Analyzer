import numpy as np
import json
from backend.chord.vocabulary import get_btc_index_map

idx_to_chord = get_btc_index_map()
chord_to_idx = {v: k for k, v in idx_to_chord.items()}

print("C:min idx:", chord_to_idx.get("C:min"))
print("C:min7 idx:", chord_to_idx.get("C:min7"))
print("A#:maj idx:", chord_to_idx.get("A#"))
print("A#:maj7 idx:", chord_to_idx.get("A#:maj7"))
