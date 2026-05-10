"""
GO Plus + Emulator — Entry Point

Usage:
  python3 -m goplusplus [options]
  python3 main.py [options]

Options:
  --no-auto-catch   Disable automatic Pokemon catching
  --no-auto-spin    Disable automatic PokéStop spinning
  --debug           Enable DEBUG-level logging
"""

import asyncio
import argparse
import logging
import signal
import sys

from goplusplus.peripheral import GOPlusPeripheral
from goplusplus.controller import GOPlusController


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pokemon GO Plus + BLE Emulator")
    p.add_argument("--no-auto-catch", action="store_true",
                   help="Disable auto-catching Pokemon")
    p.add_argument("--no-auto-spin",  action="store_true",
                   help="Disable auto-spinning PokéStops")
    p.add_argument("--debug",         action="store_true",
                   help="Enable debug logging")
    return p.parse_args()


async def run(args: argparse.Namespace):
    logger = logging.getLogger("main")
    logger.info("=== Pokemon GO Plus + Emulator ===")

    peripheral  = GOPlusPeripheral()
    controller  = GOPlusController(peripheral)

    if args.no_auto_catch:
        controller.auto_catch = False
        logger.info("Auto-catch disabled")
    if args.no_auto_spin:
        controller.auto_spin = False
        logger.info("Auto-spin disabled")

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    loop.add_signal_handler(signal.SIGINT,  stop.set)
    loop.add_signal_handler(signal.SIGTERM, stop.set)

    try:
        await peripheral.start_advertising()
        logger.info("Advertising. Waiting for Pokemon GO to connect...")
        await stop.wait()
    finally:
        await peripheral.stop()
        logger.info("Stopped.")


def main():
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
