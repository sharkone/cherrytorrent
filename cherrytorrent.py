################################################################################
import argparse
import cherrytorrent

################################################################################
def main():
    arg_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument('-hp',  '--http-port', type=int, default=8080, help='Port used for HTTP server')
    arg_parser.add_argument('-hl',  '--http-log-dir', default='.', help='Log file destination directory')
    arg_parser.add_argument('-tp',  '--torrent-port', type=int, default=6900, help='Port used for BitTorrent incoming connections')
    arg_parser.add_argument('-tdl', '--torrent-download-rate', type=int, default=0, help='Maximum download rate in kB/s, 0 = Unlimited')
    arg_parser.add_argument('-tul', '--torrent-upload-rate', type=int, default=0, help='Maximum upload rate in kB/s, 0 = Unlimited')
    arg_parser.add_argument('-tk',  '--torrent-keep-files', dest='torrent_keep_files', action='store_true', help='Keep downloaded files upon stopping')
    args = arg_parser.parse_args()

    http_config    = {
                        'port':     args.http_port,
                        'log_dir':  args.http_log_dir,
                     }

    torrent_config = {
                        'port':                 args.torrent_port,
                        'max_download_rate':    args.torrent_download_rate,
                        'max_upload_rate':      args.torrent_upload_rate,
                        'keep_files':           args.torrent_keep_files
                     }
    
    server = cherrytorrent.Server(http_config, torrent_config)
    server.run()

################################################################################
if __name__ == '__main__':
    main()
