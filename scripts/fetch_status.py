"""Runs in GitHub Actions. Reads tokens from secrets, fetches order state,
and updates status.json with the stage only. Prints nothing sensitive."""
import asyncio, json, os, sys, datetime
sys.path.insert(0, os.path.dirname(__file__))
from rivian_orders import fetch_order_states

# Fill this in after the first local probe. Keys are Rivian state strings,
# values are widget stages: ordered, confirmed, production, shipped,
# scheduled, delivered.
STATE_TO_STAGE = {
    "PENDING_FULFILLMENT": "ordered",   # confirmed from a real R2 order
    # Add new values here as Rivian's status changes, e.g.:
    # "SOME_RIVIAN_STATE": "in production stage key",
}
FIELDS = ("fulfillmentSummaryStatus", "state", "configurationStatus")

def widget_fields(snap):
    """Display-only fields from the API. Skips anything missing."""
    out = {}
    if snap.get("configurationStatus"):
        out["config_status"] = snap["configurationStatus"]
    od = snap.get("orderDate")
    if od:
        try:
            d = datetime.datetime.fromisoformat(od.replace("Z", "+00:00"))
            out["reserved"] = f"{d:%B} {d.day}, {d.year}"
        except ValueError:
            pass
    opts, ids = {}, {}
    for item in snap.get("items") or []:
        cfg = (item or {}).get("configuration") or {}
        for o in cfg.get("options") or []:
            opts[o.get("groupId")] = o.get("optionName")
            if o.get("optionId"):
                ids[o.get("groupId")] = o["optionId"]
    parts = [opts[k] for k in ("EXP", "INT", "WHL") if opts.get(k)]
    if parts:
        out["config"] = " · ".join(parts)
    # Rivian's own studio render of this exact configuration (front angle).
    seg = []
    for key in ("BLD", "EXP", "TOW", "WHL"):
        if ids.get(key) and "-" in ids[key]:
            seg.append(f"{key.lower()}-{ids[key].split('-', 1)[1].lower()}")
    if len(seg) >= 3:
        out["image"] = ("https://media.rivian.com/rivian-main/unreal-v2/r2/exterior/"
                        "angle-0_bg-studio_" + "_".join(seg) + ".webp")
    return out

def pick_stage(snapshots):
    for snap in snapshots:
        for f in FIELDS:
            stage = STATE_TO_STAGE.get(snap.get(f))
            if stage:
                return stage
    return None

async def main():
    states = await fetch_order_states(
        os.environ["RIVIAN_APP_SESSION_TOKEN"],
        os.environ["RIVIAN_CSRF_TOKEN"],
        os.environ["RIVIAN_USER_SESSION_TOKEN"],
    )
    if not states:
        print("No orders returned; status.json unchanged")
        return
    # Prefer an order whose status we recognize; otherwise the first one.
    snap = next((x for x in states if pick_stage([x])), states[0])
    stage = pick_stage([snap])
    with open("status.json") as f:
        data = json.load(f)
    new = {
        "state": snap.get("state"),
        "fulfillment": snap.get("fulfillmentSummaryStatus"),
        **widget_fields(snap),
    }
    if stage:
        new["stage"] = stage
    else:
        # Status enums only (no personal data), so safe to log.
        print(f"Unmapped status: {new['state']} / {new['fulfillment']}")
    if all(data.get(k) == v for k, v in new.items()):
        print("Status unchanged")
        return
    data.update(new)
    data["updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    with open("status.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Status updated: {new['state']} / {new['fulfillment']}")

try:
    asyncio.run(main())
except Exception as e:
    # Class name only: never print messages or responses in a public log.
    print(f"Fetch failed: {type(e).__name__}")
    sys.exit(1)
