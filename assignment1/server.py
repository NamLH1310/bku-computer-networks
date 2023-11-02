import asyncio
import logging
import json
import threading
import time

class UnknownCommandError(Exception):
    def __init__(self, cmd):
        self.cmd = cmd

    def __str__(self):
        return f'unknown command: {self.cmd}'


logging.basicConfig(format='%(asctime)s %(lineno)d %(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Connected client records
clients = {}
database = {}

status_bad_request = 404
status_ok = 200
status_internal_error = 500

status_messeage = {
    status_bad_request: 'bad request',
    status_ok: 'ok',
    status_internal_error: 'internal error',
}

async def show_tasks():
    """FOR DEBUGGING"""
    while True:
        await asyncio.sleep(5)
        logger.debug(asyncio.Task.all_tasks())


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
        del clients[client_id]
        del database[client_id]

    task = asyncio.ensure_future(client_task(reader, writer))
    task.add_done_callback(client_cleanup)

    # Add the client and the task to client records
    clients[client_id] = task
    database[client_id] = {}


async def client_task(reader, writer):
    client_addr = writer.get_extra_info('peername')
    logger.info('Start echoing back to {}'.format(client_addr))

    while True:
        data = await reader.read(1024)
        if data == b'':
            logger.info('Received EOF. Client disconnected.')
            return
        else:
            try:
                resp = handle_request(data.decode('utf-8'))
            except json.decoder.JSONDecodeError:
                resp = bytes(json.dumps({'status_code': status_bad_request, 'message': status_messeage[status_bad_request]}) + '\n', 'utf-8')
            except Exception as e:
                logger.error(e)
            finally:
                if isinstance(resp, str):
                    resp = bytes(resp + '\n', 'utf-8')
                elif not isinstance(resp, bytes):
                    resp = bytes(json.dumps({'status_code': status_internal_error, 'message': status_messeage[status_internal_error]}) + '\n', 'utf-8')

                writer.write(resp)
                await writer.drain()

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

def handle_request(request):
    pass

def parse_cmd(cmd_str):
    cmd_args = cmd_str.split()
    cmd = cmd_args[0]
    hostname = cmd_args[1]
    if cmd not in ('discover', 'ping'):
        raise UnknownCommandError(cmd_str)
    return cmd, hostname


def print_usage():
    print('usage: [discover | ping] <hostname>')

def handle_discover(hostname):
    """TODO"""

def handle_ping(hostname):
    """TODO"""

def shell_command_handler():
    time.sleep(0.5)
    while True:
        print('> ', end='')
        try:
            cmd, hostname = parse_cmd(input())
            if cmd == 'discover':
                handle_discover(hostname)
            elif cmd == 'ping':
                handle_ping(hostname)

        except UnknownCommandError as e:
            print_usage()
        except IndexError:
            print_usage()

if __name__ == '__main__':
    host = '0.0.0.0'
    port = 9009

    try:
        t = threading.Thread(target=shell_command_handler)
        t.daemon = True
        t.start()

        listen_and_serve(host, port)
    except KeyboardInterrupt as e:
        pass
    except Exception as e:
        logger.error(e)


