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

        self.bus.log('[Downloader] Applying session settings')
        session_settings = self.session.settings()
        session_settings.announce_to_all_tiers = True
        session_settings.announce_to_all_trackers = True
        session_settings.connection_speed = 100
        session_settings.peer_connect_timeout = 2
        session_settings.rate_limit_ip_overhead = True
        session_settings.request_timeout = 5
        session_settings.torrent_connect_boost = 100

        if self.torrent_config['download_rate'] > 0:
            session_settings.download_rate_limit = self.torrent_config['download_rate'] * 1024
        if self.torrent_config['upload_rate'] > 0:
            session_settings.upload_rate_limit = self.torrent_config['upload_rate'] * 1024
        self.session.set_settings(session_settings)

        self.bus.log('[Downloader] Applying encryption settings')
        encryption_settings = libtorrent.pe_settings()
        encryption_settings.out_enc_policy = libtorrent.enc_policy(self.torrent_config['encryption'])
        encryption_settings.in_enc_policy = libtorrent.enc_policy(self.torrent_config['encryption'])
        encryption_settings.allowed_enc_level = libtorrent.enc_level.both
        encryption_settings.prefer_rc4 = True
        self.session.set_pe_settings(encryption_settings)

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
