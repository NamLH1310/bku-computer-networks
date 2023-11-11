import json
from _thread import *
import time
import socket
import logging
import file_transfer
from multiprocessing import Pipe

ping_channel_read, ping_channel_write = Pipe(duplex=False)

class UnknownCommandError(Exception):
    def __init__(self, cmd):
        self.cmd = cmd

    def __str__(self):
        return f'unknown command: {self.cmd}'


logging.basicConfig(format='%(asctime)s %(lineno)d %(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Connected client records
clients = {

}

database = {

}

status_bad_request = 404
status_ok = 200
status_internal_error = 500

status_messeage = {
    status_bad_request: 'bad request',
    status_ok: 'ok',
    status_internal_error: 'internal error',
}


def listen_and_serve(host, port):
    global clients

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(100)

    while True:
        conn, client_addr = server.accept()
        clients[client_addr] = conn

        start_new_thread(handle_conn, (conn, client_addr))
    
def handle_fetch_request(raw_req: bytes):
    """ Find all peers that contain the requested file and are currently active

    Args:
        parsed_req (bytes): raw `fetch` request received from a client

    Returns:
        bytes: A JSON response containing peers' addresses.
    """

    parsed_rq = json.loads(raw_req)
    fname = parsed_rq['fname']
    if fname not in database:
        return json.dumps([])
    peers = database[fname]
    return json.dumps(peers).encode()

def handle_request(request):
    parsed_rq = json.loads(request)
    if parsed_rq['op'] == 'fetch':
        return handle_fetch_request(parsed_rq)

def handle_conn(conn, client_addr):
    try:
        while True:
            message = conn.recv(2048)
            if message == b'':
                return
            elif message == b'OK':
                ping_channel_write.send(message.decode('utf-8'))
            elif file_transfer.is_fetch_request(message):
                # Response for the `fetch` request from a peer
                resp = handle_fetch_request(message)
                conn.send(resp)
            else:
            # TODO:
            # handle 'fetch' and 'publish' request from client here
                pass
    finally:
        conn.close()
        del clients[client_addr]

def print_usage():
    print('usage: [discover | ping] <hostname>')

def handle_discover(conn):
    """TODO"""

def handle_ping(conn):
    conn.send(bytes('ping', 'utf-8'))
    while True:
        val = ping_channel_read.recv()
        if val:
            print(f'Status: {val}')
            break


def parse_cmd(cmd_str):
    cmd_args = cmd_str.split()
    cmd = cmd_args[0]
    hostname = cmd_args[1]
    if cmd not in ('discover', 'ping'):
        raise UnknownCommandError(cmd_str)
    return cmd, hostname

def user_input_handler():
    while True:
        print('> ', end='')
        try:
            cmd, hostname = parse_cmd(input())
            host_founded = False
            for (host, _), conn in clients.items():
                if cmd == 'discover' and host == hostname:
                    handle_discover(conn)
                    host_founded = True
                elif cmd == 'ping' and host == hostname:
                    handle_ping(conn)
                    host_founded = True

            if not host_founded:
                print('Host not found')

        except UnknownCommandError as e:
            print_usage()
        except IndexError:
            print_usage()

if __name__ == '__main__':
    host = '127.0.0.1'
    port = 9009

    try:
        start_new_thread(user_input_handler, ())
        listen_and_serve(host, port)
    except KeyboardInterrupt as e:
        pass
    except Exception as e:
        logger.error(e)


