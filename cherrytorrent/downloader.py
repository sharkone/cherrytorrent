################################################################################
import libtorrent

################################################################################
class Downloader:
    ############################################################################
    def __init__(self, magnet, download_dir):
        self.magnet       = magnet
        self.download_dir = download_dir

    ############################################################################
    def start(self):
        self.session = libtorrent.session()
        self.session.start_dht()
        self.session.start_lsd()
        self.session.start_upnp()
        self.session.start_natpmp()
        self.session.listen_on(6881, 6891)

        add_torrent_params                 = {}
        add_torrent_params['url']          = self.magnet
        add_torrent_params['save_path']    = self.download_dir
        add_torrent_params['storage_mode'] = libtorrent.storage_mode_t.storage_mode_sparse

        self.handle = self.session.add_torrent(add_torrent_params)
        self.handle.set_sequential_download(True)

    ############################################################################
    def stop(self):
        self.session.stop_natpmp()
        self.session.stop_upnp()
        self.session.stop_lsd()
        self.session.stop_dht()

    ############################################################################
    def get_status(self):
        status    = self.handle.status()
        state_str = ['queued', 'checking', 'downloading metadata', 'downloading', 'finished', 'seeding', 'allocating']
        return '%.2f%% complete (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % (status.progress * 100, status.download_rate / 1000, status.upload_rate / 1000, status.num_peers, state_str[status.state])
