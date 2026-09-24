import json

with open("storage/exports/test_analysis.json", "r", encoding="utf-8") as f:
    d = json.load(f)

print("Title:", d.get("title"))
print("Key:", d.get("key"))
print("BPM:", d.get("tempo"))
print("Meter:", d.get("meter"))
print("\n=== DEBUG VIEW (Bars 8 to 26) ===")
for b in d.get("debug_view", [])[7:26]:
    print(f"Bar {b['bar_number']:02d} ({b['time']}):")
    print(f"   Raw:      {b['raw_predictions']}")
    print(f"   Pooled:   {b['beat_pooled']}")
    print(f"   Bass:     {b['sounding_bass']}")
    print(f"   Final:    | {b['final_display']} |")

print("\n=== DETAILED CHORD EVIDENCE (Bars 9-16) ===")
for i, c in enumerate(d.get("chords", [])[32:64]):
    print(f"Chord {i+32} ({c['start_time']:.2f}s - {c['end_time']:.2f}s): {c['display']} (Root: {c['root']}, Qual: {c['quality']}, Bass: {c['bass']}, Conf: {c['confidence']})")
    print(f"   Alts: {c.get('alternatives', [])}")

