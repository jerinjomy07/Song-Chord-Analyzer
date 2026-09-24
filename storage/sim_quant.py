import json

with open("storage/exports/test_analysis.json", "r", encoding="utf-8") as f:
    d = json.load(f)

debug = d.get("debug_view", [])

print("BAR ALIGNMENT SIMULATION (Half-bar quantization):")
for b in debug[8:30]:
    raw = b["raw_predictions"]
    pooled = b["beat_pooled"]
    # Clean any 'N' if there are chords
    has_chords = any(c != 'N' for c in pooled)
    if has_chords:
        last = 'N'
        for i in range(len(pooled)):
            if pooled[i] == 'N':
                pooled[i] = last if last != 'N' else next((c for c in pooled if c != 'N'), 'N')
            else:
                last = pooled[i]

    # Half-bar logic for 4 beats:
    if len(pooled) == 4:
        h1 = pooled[0] # or mode(pooled[0], pooled[1])
        h2 = pooled[2] if pooled[2] == pooled[3] else (pooled[2] if pooled[0] == pooled[1] else pooled[2])
        if pooled[0] != pooled[1] and pooled[2] != pooled[3]:
            # Walkdown
            res = "  ".join(pooled)
        elif h1 == h2:
            res = h1
        else:
            res = f"{h1}   {h2}"
    else:
        res = " ".join(pooled)

    print(f"Bar {b['bar_number']:02d}: {res:<20} (was: {b['final_display']})")
