################################################################################
import argparse
import cherrytorrent

from cherrytorrent import server

################################################################################
def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('torrent_uri', help='Magnet link or torrent file URL')
    arg_parser.add_argument('-hp', '--http-port', type=int, default=8080, help='Port used for HTTP server')
    arg_parser.add_argument('-ht', '--http-inactivity-timeout', type=int, default=30, help='Inactivity timeout')
    arg_parser.add_argument('-tl', '--torrent-low-port', type=int, default=6900, help='Lower bound of BitTorrent session port range')
    arg_parser.add_argument('-th', '--torrent-high-port', type=int, default=6999, help='Higher bound of BitTorrent session port range')
    arg_parser.add_argument('-td', '--torrent-download-dir', default='.', help='Directory to use for downloading')
    arg_parser.add_argument('-tk', '--torrent-keep-files', default=False, help='Keep downloaded files upon stopping')
    args = arg_parser.parse_args()

    server = cherrytorrent.server.Server(args.http_port,
                                         args.http_inactivity_timeout,
                                         args.torrent_low_port,
                                         args.torrent_high_port,
                                         args.torrent_uri,
                                         args.torrent_download_dir,
                                         args.torrent_keep_files)
    server.run()

################################################################################
if __name__ == '__main__':
    main()
