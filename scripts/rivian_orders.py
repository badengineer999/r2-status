"""Shared helper: ask Rivian for order details, requesting ONLY safe fields
(status, dates, configuration option names). Never requests addresses,
payments, email, phone, VIN or IDs. Tries richer queries first and falls
back to simpler ones if Rivian rejects a field name."""
import aiohttp

GQL_URL = "https://rivian.com/api/gql/orders/graphql/"
HEAD = "query vehicleOrders { searchOrders(input: {orderTypes: [PRE_ORDER, VEHICLE], pageInfo: {from: 0, size: 20}}) { data { %s } } }"
QUERIES = [
    HEAD % "state fulfillmentSummaryStatus configurationStatus orderDate "
           "items { title configuration { options { groupId optionId optionName } } }",
    HEAD % "state fulfillmentSummaryStatus configurationStatus orderDate "
           "items { title configuration { options { groupId optionName } } }",
    HEAD % "state fulfillmentSummaryStatus configurationStatus orderDate",
    HEAD % "state fulfillmentSummaryStatus",
]

async def fetch_order_states(app_session, csrf, user_session, debug=False):
    """Returns a list of order dicts containing only the requested safe fields.
    debug=True (local runs only) prints Rivian's validation messages."""
    headers = {
        "content-type": "application/json",
        "apollographql-client-name": "com.rivian.ios.consumer-apollo-ios",
        "a-sess": app_session,
        "csrf-token": csrf,
        "u-sess": user_session,
    }
    async with aiohttp.ClientSession() as http:
        for n, query in enumerate(QUERIES, 1):
            async with http.post(GQL_URL, json={"query": query}, headers=headers) as r:
                text = await r.text()
                try:
                    body = await r.json(content_type=None)
                except Exception:
                    body = {}
            errors = body.get("errors") if isinstance(body, dict) else None
            if r.status == 200 and not errors:
                if debug:
                    print(f"Query variant {n} of {len(QUERIES)} worked")
                data = (body.get("data") or {}).get("searchOrders") or {}
                return data.get("data") or []
            if debug:
                msgs = [e.get("message") for e in (errors or [])] or [text[:300]]
                print(f"Variant {n} failed (HTTP {r.status}): {msgs}")
            if r.status in (401, 403):
                break
    raise RuntimeError("all query variants failed")
