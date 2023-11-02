import argparse
import time
import threading
import asyncio
import logging

logging.basicConfig(format='%(asctime)s %(lineno)d %(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

class UnknownCommandError(Exception):
    def __init__(self, cmd):
        self.cmd = cmd

    def __str__(self):
        return f'unknown command: {self.cmd}'


def parse_cmd(cmd_str):
    cmd_args = cmd_str.split()
    cmd = cmd_args[0]
    if cmd not in ('publish', 'fetch'):
        raise UnknownCommandError(cmd_str)

    if cmd == 'publish':
        lname, fname = cmd_args[1], cmd_args[2]
        return cmd, (lname, fname)

    return cmd, cmd_args[1]

def print_usage():
    print('usage: publish <lname> <fname> | fetch <fname>')

def handle_publish(lname, fname):
    """TODO: publish file to server"""

def handle_fetch(fname):
    """TODO: send request to peer"""

def shell_command_handler():
    time.sleep(0.5)
    while True:
        print('> ', end='')
        try:
            cmd, args = parse_cmd(input())
            if cmd == 'publish':
                handle_publish(args[0], args[1])
            elif cmd == 'fetch':
                handle_fetch(args)
        except UnknownCommandError as e:
            print_usage()
        except IndexError:
            print_usage()


def client_connected_cb(reader, writer):
    # Use peername as client ID
    client_id = writer.get_extra_info('peername')

    logger.info('Client connected: {}'.format(client_id))

    # Define the clean up function here
    def client_cleanup(fu):
        logger.info('Cleaning up client {}'.format(client_id))
        try:  # Retrievre the result and ignore whatever returned, since it's just cleaning
            fu.result()
        except Exception as e:
            pass
        # Remove the client from client records

    task = asyncio.ensure_future(client_task(reader, writer))
    task.add_done_callback(client_cleanup)

async def client_task(reader, writer):
    client_addr = writer.get_extra_info('peername')
    logger.info('Start echoing back to {}'.format(client_addr))

    while True:
        data = await reader.read(1024)
        if data == b'':
            logger.info('Received EOF. Client disconnected.')
            return
        else:
            # TODO
            # handle 'ping' and 'discover' request from the server
            # handle request for downloading file: use ftp


def listen_and_serve(host, port):
    loop = asyncio.get_event_loop()
    server_coroutine = asyncio.start_server(client_connected_cb,
                                       host=host,
                                       port=port,
                                       loop=loop)
    server = loop.run_until_complete(server_coroutine)

    try:
        logger.info('Serving on {}:{}'.format(host, port))
        loop.run_forever()
    except Exception as e:
        raise e
    finally:
        # Close the server
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-H', '--server-host')
    arg_parser.add_argument('-P', '--server-port')
    args = arg_parser.parse_args()
    server_hostname = args.server_host or 'localhost'
    server_port = int(args.server_port or '8080')

    t = threading.Thread(target=shell_command_handler)
    t.daemon = True
    t.start()

    listen_and_serve('0.0.0.0', 8080)

