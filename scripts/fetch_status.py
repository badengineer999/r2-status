"""Runs in GitHub Actions. Reads tokens from secrets, fetches order state,
and updates status.json with the stage only. Prints nothing sensitive."""
import asyncio, json, os, sys, datetime
sys.path.insert(0, os.path.dirname(__file__))
from rivian_orders import fetch_order_states

# Fill this in after the first local probe. Keys are Rivian state strings,
# values are widget stages: ordered, confirmed, production, shipped,
# scheduled, delivered.
STATE_TO_STAGE = {
    # "SOME_RIVIAN_STATE": "confirmed",
}
FIELDS = ("fulfillmentSummaryStatus", "state", "configurationStatus")

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
    stage = pick_stage(states)
    if not stage:
        print("No mapped stage found; status.json unchanged")
        return
    with open("status.json") as f:
        data = json.load(f)
    if data.get("stage") == stage:
        print("Stage unchanged")
        return
    data["stage"] = stage
    data["updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    with open("status.json", "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"Stage updated to {stage}")

try:
    asyncio.run(main())
except Exception as e:
    # Class name only: never print messages or responses in a public log.
    print(f"Fetch failed: {type(e).__name__}")
    sys.exit(1)
