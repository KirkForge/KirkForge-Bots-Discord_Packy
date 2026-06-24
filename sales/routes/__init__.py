"""Routes package for the sales service.

Submodules are mounted into the FastAPI app via their `mount(app, ...)`
function. Keeping each route module independently mountable lets us
disable a route in tests by simply not mounting it.
"""
