################################################################################
import argparse
import cherrytorrent

from cherrytorrent import server

################################################################################
def main():
    arg_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument('torrent_uri', help='Magnet link or torrent file URL')
    arg_parser.add_argument('-hp',  '--http-port', type=int, default=8080, help='Port used for HTTP server')
    arg_parser.add_argument('-ht',  '--http-inactivity-timeout', type=int, default=30, help='Inactivity timeout')
    arg_parser.add_argument('-tp',  '--torrent-port', type=int, default=6900, help='Port used for BitTorrent incoming connections')
    arg_parser.add_argument('-tdl', '--torrent-download-rate', type=int, default=0, help='Maximum download rate in kB/s, 0 = Unlimited')
    arg_parser.add_argument('-tul', '--torrent-upload-rate', type=int, default=0, help='Maximum upload rate in kB/s, 0 = Unlimited')
    arg_parser.add_argument('-te',  '--torrent-encryption', default=1, help='Encryption mode, 0: Forced, 1: Enabled, 2: Disabled')
    arg_parser.add_argument('-td',  '--torrent-download-dir', default='.', help='Directory to use for downloading')
    arg_parser.add_argument('-tk',  '--torrent-keep-files', dest='torrent_keep_files', action='store_true', help='Keep downloaded files upon stopping')
    args = arg_parser.parse_args()

    http_config    = {
                        'port':                 args.http_port,
                        'inactivity_timeout':   args.http_inactivity_timeout
                     }

    torrent_config = {
                        'uri':              args.torrent_uri,
                        'port':             args.torrent_port,
                        'download_rate':    args.torrent_download_rate,
                        'upload_rate':      args.torrent_upload_rate,
                        'encryption':       args.torrent_encryption,
                        'download_dir':     args.torrent_download_dir,
                        'keep_files':       args.torrent_keep_files
                     }
    
    server = cherrytorrent.server.Server(http_config, torrent_config)
    server.run()

################################################################################
if __name__ == '__main__':
    main()
