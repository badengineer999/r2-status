"""Shared helper: ask Rivian for the order state fields and nothing else.
UNTESTED against the live API; endpoint and query come from community docs."""
import aiohttp

GQL_URL = "https://rivian.com/api/gql/gateway/graphql"
QUERY = """
query getOrders {
  user {
    orderSnapshots(filterTypes: [PRE_ORDER, VEHICLE, RETAIL]) {
      state
      configurationStatus
      fulfillmentSummaryStatus
    }
  }
}
"""

async def fetch_order_states(app_session, csrf, user_session):
    """Returns a list of dicts with ONLY state fields (no IDs, VINs, prices)."""
    headers = {
        "content-type": "application/json",
        "apollographql-client-name": "com.rivian.ios.consumer-apollo-ios",
        "a-sess": app_session,
        "csrf-token": csrf,
        "u-sess": user_session,
    }
    async with aiohttp.ClientSession() as http:
        async with http.post(GQL_URL, json={"query": QUERY}, headers=headers) as r:
            r.raise_for_status()
            body = await r.json()
    if body.get("errors"):
        raise RuntimeError("graphql error")
    snaps = (body.get("data") or {}).get("user", {}).get("orderSnapshots") or []
    keep = ("state", "configurationStatus", "fulfillmentSummaryStatus")
    return [{k: s.get(k) for k in keep} for s in snaps]
