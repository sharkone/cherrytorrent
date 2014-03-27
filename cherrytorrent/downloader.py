################################################################################
import cherrypy
import libtorrent

################################################################################
class DownloaderPlugin(cherrypy.process.plugins.SimplePlugin):
    ############################################################################
    def __init__(self, bus, torrent_config):
        cherrypy.process.plugins.SimplePlugin.__init__(self, bus)
        
        self.torrent_config = torrent_config
        self.torrent_handle = None

    ############################################################################
    def start(self):
        self.bus.log('[Downloader] Starting')
        self.session = libtorrent.session()
        self.session.start_dht()
        self.session.start_lsd()
        self.session.start_upnp()
        self.session.start_natpmp()
        self.bus.log('[Downloader] Listening on {0}:{1}'.format(self.torrent_config['low_port'], self.torrent_config['high_port']))
        self.session.listen_on(self.torrent_config['low_port'], self.torrent_config['high_port'])

        self.bus.log('[Downloader] Setting session settings')
        if self.torrent_config['download_rate'] > 0:
            self.session.settings().download_rate_limit = self.torrent_config['download_rate'] * 1024
        if self.torrent_config['upload_rate'] > 0:
            self.session.settings().upload_rate_limit = self.torrent_config['upload_rate'] * 1024

        self.bus.log('[Downloader] Adding requested torrent')
        add_torrent_params                 = {}
        add_torrent_params['url']          = self.torrent_config['uri']
        add_torrent_params['save_path']    = self.torrent_config['download_dir']
        add_torrent_params['storage_mode'] = libtorrent.storage_mode_t.storage_mode_sparse

        self.torrent_handle = self.session.add_torrent(add_torrent_params)
        self.torrent_handle.set_sequential_download(True)

        torrent_handle_status = self.torrent_handle.status()
        if torrent_handle_status.error:
            raise RuntimeError(torrent_handle_status.error)

    ############################################################################
    def stop(self):
        self.bus.log('[Downloader] Stopping')
        if self.torrent_handle:
            if not self.torrent_config['keep_files']:
                self.bus.log('[Downloader] Removing downloaded files')
                self.session.set_alert_mask(libtorrent.alert.category_t.storage_notification)
                self.session.remove_torrent(self.torrent_handle, libtorrent.options_t.delete_files)
                self.session.wait_for_alert(30)

        self.session.stop_natpmp()
        self.session.stop_upnp()
        self.session.stop_lsd()
        self.session.stop_dht()

    ############################################################################
    def get_status(self):
        status    = self.torrent_handle.status()
        state_str = ['queued', 'checking', 'downloading metadata', 'downloading', 'finished', 'seeding', 'allocating']
        return '%.2f%% complete (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % (status.progress * 100, status.download_rate / 1000, status.upload_rate / 1000, status.num_peers, state_str[status.state])
