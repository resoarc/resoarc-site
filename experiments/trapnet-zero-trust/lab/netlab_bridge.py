#!/usr/bin/env python3
"""EXPIRING TEST ADAPTER: bridges loopback-only binaries inside Docker internal networks.

This file is NOT a production ingress service. It refuses to start unless explicitly
launched by the controlled Docker lab. Docker must not publish any container ports.
"""
import argparse
import asyncio
import os
import signal
import subprocess
import sys

LAB_MARKER = "TRAPNET_V09_INTERNAL_LAB_ONLY"

async def forward(src_reader, dst_writer):
    try:
        while True:
            data = await src_reader.read(8192)
            if not data:
                break
            dst_writer.write(data)
            await dst_writer.drain()
    except (BrokenPipeError, ConnectionError, OSError):
        pass
    finally:
        try:
            dst_writer.close()
        except OSError:
            pass

async def bridge_client(reader, writer, host, port):
    try:
        target_reader, target_writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=3
        )
        await asyncio.gather(forward(reader, target_writer), forward(target_reader, writer))
    except (OSError, asyncio.TimeoutError):
        writer.close()
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    if os.environ.get('TRAPNET_NETLAB_MARKER') != LAB_MARKER:
        raise RuntimeError('isolated lab marker missing; refusing network bridge')
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='role', required=True)
    h = sub.add_parser('hub')
    h.add_argument('--binary', required=True)
    h.add_argument('--allowlist', required=True)
    h.add_argument('--ledger', required=True)
    h.add_argument('--port', type=int, default=18788)
    s = sub.add_parser('sensor')
    s.add_argument('--binary', required=True)
    s.add_argument('--key', required=True)
    s.add_argument('--fingerprint', required=True)
    args = ap.parse_args()
    if args.role == 'hub':
        if args.port != 18788:
            raise RuntimeError('unexpected lab relay port')
        process = subprocess.Popen([args.binary, '-allowlist', args.allowlist, '-ledger', args.ledger],
                                   stdout=sys.stderr, stderr=sys.stderr)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError('HUB quit before bridge was ready')
                try:
                    check_reader, check_writer = await asyncio.open_connection('127.0.0.1', 8788)
                    check_writer.close()
                    await check_writer.wait_closed()
                    break
                except OSError:
                    await asyncio.sleep(.05)
            else:
                raise RuntimeError('HUB loopback readiness timed out')
            server = await asyncio.start_server(
                lambda r, w: bridge_client(r, w, '127.0.0.1', 8788), '0.0.0.0', args.port
            )
            async with server:
                while process.poll() is None:
                    await asyncio.sleep(.1)
            raise RuntimeError('HUB terminated during the isolation lab')
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
    else:
        # The shipping Sensor may only connect to 127.0.0.1; keep that invariant.
        server = await asyncio.start_server(
            lambda r, w: bridge_client(r, w, 'hub', 18788), '127.0.0.1', 8788
        )
        async with server:
            process = await asyncio.create_subprocess_exec(
                args.binary, '-key', args.key, '-fingerprint', args.fingerprint,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            output, errors = await asyncio.wait_for(process.communicate(), timeout=15)
            sys.stdout.write(output.decode('utf-8', errors='replace'))
            sys.stderr.write(errors.decode('utf-8', errors='replace'))
            if process.returncode:
                raise RuntimeError('Sensor failed with code ' + str(process.returncode))

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as exc:
        print('TrapNet isolated lab refused: '+str(exc), file=sys.stderr)
        sys.exit(1)
