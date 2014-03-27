################################################################################
import argparse
import cherrytorrent

from cherrytorrent import server

################################################################################
def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('uri', help='Magnet link or torrent file URL')
    arg_parser.add_argument('-p', '--http-port', type=int, default=8080, help='Port used for HTTP server')
    arg_parser.add_argument('-d', '--download-dir', default='.', help='Directory to use for downloading')
    arg_parser.add_argument('-t', '--inactivity-timeout', type=int, default=30, help='Inactivity timeout')
    arg_parser.add_argument('-k', '--keep-files', default=False, help='Keep downloaded files upon stopping')
    args = arg_parser.parse_args()

    server = cherrytorrent.server.Server(args.http_port, args.inactivity_timeout, args.uri, args.download_dir, args.keep_files)
    server.run()

################################################################################
if __name__ == '__main__':
    main()
