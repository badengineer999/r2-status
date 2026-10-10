"""Shared helper: ask Rivian for order state fields and nothing else.
Endpoint and query follow community-documented traffic; may need tweaks."""
import aiohttp

GQL_URL = "https://rivian.com/api/gql/orders/graphql/"
QUERY = """
query vehicleOrders {
  searchOrders(input: {orderTypes: [PRE_ORDER, VEHICLE], pageInfo: {from: 0, size: 20}}) {
    data {
      state
      fulfillmentSummaryStatus
    }
  }
}
"""
KEEP = ("state", "fulfillmentSummaryStatus")

async def fetch_order_states(app_session, csrf, user_session, debug=False):
    """Returns a list of dicts with ONLY state fields (no IDs, VINs, prices).
    debug=True (local runs only) prints Rivian's error text on failure."""
    headers = {
        "content-type": "application/json",
        "apollographql-client-name": "com.rivian.ios.consumer-apollo-ios",
        "a-sess": app_session,
        "csrf-token": csrf,
        "u-sess": user_session,
    }
    async with aiohttp.ClientSession() as http:
        async with http.post(GQL_URL, json={"query": QUERY}, headers=headers) as r:
            text = await r.text()
            if r.status != 200:
                if debug:
                    print(f"HTTP {r.status}: {text[:600]}")
                r.raise_for_status()
            body = await r.json(content_type=None)
    if body.get("errors"):
        if debug:
            print("GraphQL errors:", [e.get("message") for e in body["errors"]])
        raise RuntimeError("graphql error")
    rows = ((body.get("data") or {}).get("searchOrders") or {}).get("data") or []
    return [{k: row.get(k) for k in KEEP} for row in rows]
