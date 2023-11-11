import argparse
import time
from _thread import *
import asyncio
import logging
import socket
import json
import random
import file_transfer
import sys
import socketserver

logging.basicConfig(format='%(asctime)s %(lineno)d %(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

HOST = '0.0.0.0'
PORT = 8080
PEER_SRV_PORT = None
REPOSITORY_DIR = "./"

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

def handle_publish(lname, fname, conn):
    """TODO: publish file to server"""
    host, port = server_addr

def get_peers_from_srv(fname: str, host: str, port: int):
    """ Retrieve all peers that contain 'fname' in their repositories.

    Args:
        fname(str): name of the file being requested 
        host(str): ipv4 address of the server
        port(str): port on which the server listens 

    Returns:
        list: A list of string representing peers in the following format: "{host}:{port}"
    """

    fetch_req = file_transfer.create_fetch_request(fname)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        sock.send(fetch_req)
        raw_resp = sock.recv(1024)
        peers = json.loads(raw_resp)
        return peers


def handle_fetch_cmd(fname, conn):
    """TODO: send request to server
        -> server return data consist of peer host and port
        -> send request retrieve file from peer
        -> peer send back file (using ftp)
    """

    logger.info(f"Fetching file '{fname}'...")

    """ TODO: handle the case that there exists a file named 'fname' in the repository. """

    peers = get_peers_from_srv(fname, server_host, server_port)
    logger.debug(f"Peers containing '{fname}': {peers}")

    if peers == []:
        print(f"No file named '{fname}' was published.")
        return

    # Pick a random peer
    peer: str = random.choice(peers)
    logger.debug(f"Choose peer: {peer}")

    # peer's host, peer's port
    p_host, p_port = peer

    file_transfer.fetch_file(fname=fname, host=p_host, port=p_port, file_dir=f"{REPOSITORY_DIR}")
    logger.debug(f"Fetched file '{fname}' from peer {peer}.")
    print(f"Successfully fetched {fname}.")

def shell_command_handler(conn):
    while True:
        print('> ', end='')
        try:
            cmd, args = parse_cmd(input())
            if cmd == 'publish':
                handle_publish(args[0], args[1], conn)
            elif cmd == 'fetch':
                handle_fetch_cmd(args, conn)
        except UnknownCommandError as e:
            print_usage()
        except IndexError:
            print_usage()

def handle_request_from_server(conn):
    while True:
        message = conn.recv(2048)
        if message == b'':
            sys.exit(0)
        elif message == b'ping':
            conn.send(b'OK')
        # TODO:
        # handle 'discover' request from server

class PeerRequestHandler(socketserver.BaseRequestHandler):
    def is_fetch_request(self, raw_req: bytes):
        """ Check if the raw request is a `fetch` request. """
        fields = ['op', 'fname']
        parsed_rq : dict = json.loads(raw_req)
        for field in fields:
            if field not in parsed_rq.keys():
                return False
        
        return parsed_rq['op'] == 'fetch' and isinstance(parsed_rq['fname'], str)

    def is_validate_request(self, raw_req: bytes):
        """ Check if the raw request is a `validate` request.
            A `validate` request is used to ask a peer whether the file `fname`
            still exists in its repository.
        """
        fields = ['op', 'fname']
        parsed_rq : dict = json.loads(raw_req)
        for field in fields:
            if field not in parsed_rq.keys():
                return False
        
        return parsed_rq['op'] == 'validate' and isinstance(parsed_rq['fname'], str)

    def handle(self):
        """ Handle incoming requests from other peers. """
        raw_req = self.request.recv(1024)
        if self.is_fetch_request(raw_req):
            parsed_req = json.loads(raw_req)
            fname = parsed_req['fname']
            with open(f"{REPOSITORY_DIR}/{fname}", "rb") as f:
                chunk = f.read(8192)
                while chunk:
                    self.request.send(chunk)
                    chunk = f.read(8192)

def handle_request_from_peer(peer_srv: socketserver.TCPServer):
    try:
        peer_srv.serve_forever()
    finally:
        peer_srv.server_close()

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-H', '--server-host')
    arg_parser.add_argument('-P', '--server-port')
    arg_parser.add_argument('--peer-srv-port')
    arg_parser.add_argument('--shared-repo')
    args = arg_parser.parse_args()
    server_host = args.server_host or 'localhost'
    server_port = int(args.server_port or '8080')

    # if the seeding server's port is not specified, tell Python to choose a random unused port
    PEER_SRV_PORT = int(args.peer_srv_port or 0)    
    REPOSITORY_DIR = args.shared_repo

    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.connect((server_host, server_port))

        start_new_thread(handle_request_from_server, (server,))
        peer_srv = socketserver.ThreadingTCPServer(('', PEER_SRV_PORT), PeerRequestHandler)
        PEER_SRV_PORT = peer_srv.server_address[1]
        print(f"Start listening from other peers at port {PEER_SRV_PORT}.")

        # Create new PyThread to handle request from other peers
        start_new_thread(handle_request_from_peer, (peer_srv,))

        shell_command_handler(server)
    finally:
        server.close()