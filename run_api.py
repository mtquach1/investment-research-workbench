"""Local launcher: no request URL access logs; public hosting remains separate work."""

import uvicorn


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, access_log=False)
