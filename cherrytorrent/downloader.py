################################################################################
import libtorrent

################################################################################
class Downloader:
    ############################################################################
    def __init__(self, uri, download_dir):
        self.uri          = uri
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
        add_torrent_params['url']          = self.uri
        add_torrent_params['save_path']    = self.download_dir
        add_torrent_params['storage_mode'] = libtorrent.storage_mode_t.storage_mode_sparse

        self.torrent_handle = self.session.add_torrent(add_torrent_params)
        self.torrent_handle.set_sequential_download(True)

        torrent_handle_status = self.torrent_handle.status()
        if torrent_handle_status.error:
            raise RuntimeError(torrent_handle_status.error)

    ############################################################################
    def stop(self):
        self.session.stop_natpmp()
        self.session.stop_upnp()
        self.session.stop_lsd()
        self.session.stop_dht()

    ############################################################################
    def get_status(self):
        status    = self.torrent_handle.status()
        state_str = ['queued', 'checking', 'downloading metadata', 'downloading', 'finished', 'seeding', 'allocating']
        return '%.2f%% complete (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % (status.progress * 100, status.download_rate / 1000, status.upload_rate / 1000, status.num_peers, state_str[status.state])
