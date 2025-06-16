"""
Sprint-5 placeholder for the SoulSeed FastAPI app.

— What the tests expect —
1. The file must import / create a FastAPI instance called `app`.
2. It must register a GET route at `/soulseed`.
3. It must expose an `import_main()` helper that simply returns `app`.

When you’re ready to flesh things out, replace the stub logic
inside `soulseed_root()` and add additional routes as usual.
"""

from fastapi import FastAPI

#: minimal FastAPI app the tests look for
app = FastAPI(title="SoulSeed API stub")


@app.get("/soulseed", tags=["health"])
def soulseed_root() -> dict[str, str]:
    """Health-check endpoint required by the placeholder test suite."""
    return {"status": "alive"}


def import_main():
    """
    Helper the tests call.

    Returning the FastAPI instance keeps them happy while the real
    implementation is built in later sprints.
    """
    return app
