"""Run this ON YOUR OWN MACHINE, once. Never in GitHub Actions.

  pip install rivian-python-client
  python tools/login_local.py

It signs in (with MFA), prints the three session tokens for you to paste into
GitHub -> Settings -> Secrets and variables -> Actions, then prints ONLY the
order state fields so we can map them to widget stages.
Tokens print to your terminal only. Clear the terminal afterwards and do not
paste them anywhere except GitHub secrets.
"""
import asyncio, getpass, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from rivian import Rivian
from rivian_orders import fetch_order_states

async def main():
    email = input("Rivian email: ").strip()
    password = getpass.getpass("Rivian password: ")
    r = Rivian()
    try:
        await r.create_csrf_token()
        await r.authenticate(email, password)
        if getattr(r, "_otp_needed", False):
            await r.validate_otp(email, input("Verification code: ").strip())
        tokens = {
            "RIVIAN_APP_SESSION_TOKEN": getattr(r, "_app_session_token", None),
            "RIVIAN_CSRF_TOKEN": getattr(r, "_csrf_token", None),
            "RIVIAN_USER_SESSION_TOKEN": getattr(r, "_user_session_token", None),
        }
        missing = [k for k, v in tokens.items() if not v]
        if missing:
            sys.exit(f"Login worked but these tokens were not found: {missing}")
        print("\nCreate these as GitHub Actions secrets (name = value):\n")
        for k, v in tokens.items():
            print(f"{k}\n{v}\n")
        print("Order state fields (safe to share with Claude):")
        states = await fetch_order_states(
            tokens["RIVIAN_APP_SESSION_TOKEN"],
            tokens["RIVIAN_CSRF_TOKEN"],
            tokens["RIVIAN_USER_SESSION_TOKEN"],
            debug=True,
        )
        for s in states:
            print(s)
    finally:
        close = getattr(r, "close", None)
        if close:
            await close()

asyncio.run(main())
