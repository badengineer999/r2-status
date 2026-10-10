"""Run ON YOUR OWN MACHINE. Lists the field NAMES Rivian's orders API offers
(schema only, no values, no tokens) and saves them to schema_tree.txt.

  python tools/probe_fields.py
"""
import asyncio, getpass, sys, os
import aiohttp
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from rivian import Rivian
from rivian_orders import GQL_URL

REF = "kind name ofType { kind name ofType { kind name ofType { kind name ofType { kind name } } } }"
INTRO = ("query { __schema { queryType { name } types { name kind "
         "fields { name type { " + REF + " } } } } }")

def base(t):
    while t.get("ofType"):
        t = t["ofType"]
    return t

async def main():
    email = input("Rivian email: ").strip()
    password = getpass.getpass("Rivian password: ")
    r = Rivian()
    try:
        await r.create_csrf_token()
        await r.authenticate(email, password)
        if getattr(r, "_otp_needed", False):
            await r.validate_otp(email, input("Verification code: ").strip())
        headers = {
            "content-type": "application/json",
            "apollographql-client-name": "com.rivian.ios.consumer-apollo-ios",
            "a-sess": r._app_session_token,
            "csrf-token": r._csrf_token,
            "u-sess": r._user_session_token,
        }
        async with aiohttp.ClientSession() as http:
            async with http.post(GQL_URL, json={"query": INTRO}, headers=headers) as resp:
                text = await resp.text()
                if resp.status != 200:
                    sys.exit(f"HTTP {resp.status}: {text[:400]}")
                body = await resp.json(content_type=None)
        if body.get("errors") or not body.get("data"):
            print("Introspection not allowed:", [e.get("message") for e in body.get("errors", [])])
            print("Use the browser Network-tab method instead (see Claude's message).")
            return
        schema = body["data"]["__schema"]
        types = {t["name"]: t for t in schema["types"]}
        q = types[schema["queryType"]["name"]]
        start = next((f for f in q["fields"] if f["name"] == "searchOrders"), None)
        if not start:
            sys.exit("searchOrders not found in schema")
        lines = []
        def walk(tname, depth, seen):
            t = types.get(tname)
            if not t or not t.get("fields") or depth > 4 or tname in seen:
                return
            for f in t["fields"]:
                b = base(f["type"])
                lines.append("  " * depth + f"{f['name']}: {b['name']}")
                if b["kind"] in ("OBJECT", "INTERFACE"):
                    walk(b["name"], depth + 1, seen | {tname})
        lines.append(f"searchOrders: {base(start['type'])['name']}")
        walk(base(start["type"])["name"], 1, set())
        with open("schema_tree.txt", "w") as f:
            f.write("\n".join(lines))
        print(f"Saved {len(lines)} field names to schema_tree.txt")
    finally:
        close = getattr(r, "close", None)
        if close:
            await close()

asyncio.run(main())
