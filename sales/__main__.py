"""Sales service entrypoint: `python -m sales`."""

from __future__ import annotations

import logging

import uvicorn

from sales.app import create_app
from sales.config import load_config


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    cfg = load_config()
    app = create_app(config=cfg)
    uvicorn.run(
        app,
        host=cfg.bind,
        port=cfg.port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
