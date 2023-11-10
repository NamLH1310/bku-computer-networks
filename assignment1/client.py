import argparse
import time
from _thread import *
import asyncio
import logging
import socket
import sys
import json
import os

logging.basicConfig(format='%(asctime)s %(lineno)d %(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

HOST = '0.0.0.0'
PORT = 8080

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

def handle_fetch(fname, conn):
    """TODO: send request to server
        -> server return data consist of peer host and port
        -> send request retrieve file from peer
        -> peer send back file (using ftp)
    """


def shell_command_handler(conn):
    while True:
        print('> ', end='')
        try:
            cmd, args = parse_cmd(input())
            if cmd == 'publish':
                handle_publish(args[0], args[1], conn)
            elif cmd == 'fetch':
                handle_fetch(args, conn)
        except UnknownCommandError as e:
            print_usage()
        except IndexError:
            print_usage()


def handle_request_from_server(conn):
    while True:
        message = conn.recv(4096)
        if message == b'':
            sys.exit(0)
        elif message == b'ping':
            conn.send(b'OK')
        elif message == b'discover':
            folder_path = "C:\shared_folder"
            #conn.sendall(folder_path.encode('utf-8'))
            #print("sent")
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                file_list = os.listdir(folder_path)

                # Tạo một JSON chứa thông tin tên các tệp tin
                files_data = json.dumps({'files': file_list})
                try:
                    conn.sendall(files_data.encode('utf-8'))
                    print("send data successfully")
                    print(f"Data to be sent: {files_data}")
                except socket.error as e:
                    logger.error(e)
            else:
                print(f"No folder path {folder_path}")
                # TODO:
        # handle 'discover' request from server

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-H', '--server-host')
    arg_parser.add_argument('-P', '--server-port')
    args = arg_parser.parse_args()
    server_host = args.server_host or 'localhost'
    server_port = int(args.server_port or '8080')

    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.connect((server_host, server_port))

        start_new_thread(handle_request_from_server, (server,))

        shell_command_handler(server)
    finally:
        server.close()

