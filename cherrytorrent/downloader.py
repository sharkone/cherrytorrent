################################################################################
import cherrypy
import filewrapper
import libtorrent
import math
import time
import utils

################################################################################
class DownloaderMonitor(cherrypy.process.plugins.Monitor):
    ############################################################################
    def __init__(self, bus, torrent_config):
        cherrypy.process.plugins.Monitor.__init__(self, bus, self._background_task, frequency=1)

        self.torrent_config = torrent_config

        self.session            = None
        self.torrent_handle     = None
        self.torrent_video_file = None

    ############################################################################
    def start(self):
        cherrypy.process.plugins.Monitor.start(self)

        self.bus.log('[Downloader] Starting session')
        self.session = libtorrent.session()
        self.session.set_alert_mask(libtorrent.alert.category_t.error_notification | libtorrent.alert.category_t.status_notification)
        self.session.start_dht()
        self.session.start_lsd()
        self.session.start_upnp()
        self.session.start_natpmp()
        self.session.listen_on(self.torrent_config['port'], self.torrent_config['port'])

        # Session settings
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

        # Encryption settings
        encryption_settings = libtorrent.pe_settings()
        encryption_settings.out_enc_policy = libtorrent.enc_policy(libtorrent.enc_policy.forced)
        encryption_settings.in_enc_policy = libtorrent.enc_policy(libtorrent.enc_policy.forced)
        encryption_settings.allowed_enc_level = libtorrent.enc_level.both
        encryption_settings.prefer_rc4 = True
        self.session.set_pe_settings(encryption_settings)
        
        self.bus.log('[Downloader] Adding torrent')
        add_torrent_params                 = {}
        add_torrent_params['url']          = self.torrent_config['uri']
        add_torrent_params['save_path']    = self.torrent_config['download_dir']
        add_torrent_params['storage_mode'] = libtorrent.storage_mode_t.storage_mode_sparse
        self.session.async_add_torrent(add_torrent_params)


    ############################################################################
    def stop(self):
        self.bus.log('[Downloader] Stopping session')

        if self.torrent_handle:
            if not self.torrent_config['keep_files']:
                self.bus.log('[Downloader] Removing downloaded files')
                self.session.remove_torrent(self.torrent_handle, libtorrent.options_t.delete_files)
                while self.torrent_handle:
                    time.sleep(0.1)

        self.session.stop_natpmp()
        self.session.stop_upnp()
        self.session.stop_lsd()
        self.session.stop_dht()

        cherrypy.process.plugins.Monitor.stop(self)

    ############################################################################
    def get_status(self):
        result = { 'session': {}, 'video_file':{} }

        if self.torrent_handle:
            status = self.torrent_handle.status()
            result['session']['state']         = str(status.state)
            result['session']['state_index']   = int(status.state)
            result['session']['progress']      = math.trunc(status.progress * 100.0) / 100.0
            result['session']['download_rate'] = status.download_rate / 1024
            result['session']['upload_rate']   = status.upload_rate / 1024
            result['session']['num_seeds']     = status.num_seeds
            result['session']['total_seeds']   = status.num_complete
            result['session']['num_peers']     = status.num_peers
            result['session']['total_peers']   = status.num_incomplete

        if self.torrent_video_file:
            result['video_file']['path']              = self.torrent_video_file.path
            result['video_file']['size']              = self.torrent_video_file.size
            result['video_file']['start_piece_index'] = self.torrent_video_file.start_piece_index
            result['video_file']['end_piece_index']   = self.torrent_video_file.end_piece_index
            result['video_file']['total_pieces']      = max(1, self.torrent_video_file.end_piece_index - self.torrent_video_file.start_piece_index)

            completed_pieces = 0
            for piece_index in range(self.torrent_video_file.start_piece_index, self.torrent_video_file.end_piece_index + 1):
                if self.torrent_handle.have_piece(piece_index):
                    completed_pieces = completed_pieces + 1
                else:
                    break
            result['video_file']['complete_pieces'] = completed_pieces

            piece_map = ''
            for piece_index in range(self.torrent_video_file.start_piece_index, self.torrent_video_file.end_piece_index + 1):
                if self.torrent_handle.have_piece(piece_index):
                    piece_map = piece_map + '*'
                else:
                    piece_map = piece_map + str(self.torrent_handle.piece_priority(piece_index))
            result['video_file']['piece_map'] = piece_map

        return result

    ############################################################################
    def get_video_file(self):
        if self.torrent_video_file:
            return filewrapper.FileWrapper(self.bus, self.torrent_handle, self.torrent_video_file)

    ############################################################################
    def _background_task(self):
        while not self.session:
            time.sleep(0.1)

        self.session.wait_for_alert(1000)
        alert = self.session.pop_alert()
        if alert:
            # Critical alerts
            if isinstance(alert, libtorrent.torrent_error_alert):
                self.bus.log('[Downloader] {0}: {1}'.format(alert.what(), alert.message()))
                self.torrent_handle = None
                cherrypy.engine.exit()
            
            # Ignored alerts
            elif isinstance(alert, libtorrent.add_torrent_alert):
                pass

            # Session alerts
            elif isinstance(alert, libtorrent.listen_succeeded_alert):
                # TODO: Need to fix python bindings to properly expose endpoint as tuple
                self.bus.log('[Downloader] Session {0}'.format(alert.message()))

            # Tracker alerts
            elif isinstance(alert, libtorrent.tracker_error_alert):
                self.bus.log('[Downloader] Tracker error: {0} {1}'.format(alert.url, alert.status_code))

            # Torrent alerts
            elif isinstance(alert, libtorrent.torrent_added_alert):
                self.bus.log('[Downloader] Torrent added')
                self.torrent_handle = alert.handle
                self.torrent_handle.set_sequential_download(True)
            elif isinstance(alert, libtorrent.torrent_removed_alert):
                self.bus.log('[Downloader] Torrent removed')
                self.torrent_handle = None
            elif isinstance(alert, libtorrent.state_changed_alert):
                self.bus.log('[Downloader] Torrent state changed: {0}'.format(alert.state))
                if int(alert.state) >= int(libtorrent.torrent_status.states.downloading) and int(alert.state) <= int(libtorrent.torrent_status.states.seeding):
                    self.torrent_video_file = self._get_video_torrent_file()
                    if self.torrent_video_file:
                        self.torrent_video_file.start_piece_index = utils.piece_from_offset(self.torrent_handle, self.torrent_video_file.offset)
                        self.torrent_video_file.end_piece_index   = utils.piece_from_offset(self.torrent_handle, self.torrent_video_file.offset + self.torrent_video_file.size)
                    else:
                        self.bus.log('[Downloader] No video file found')
                        cherrypy.engine.exit()

                if alert.state == libtorrent.torrent_status.states.downloading:
                    if self.torrent_video_file:
                        self.bus.log('[Downloader] Setting pieces priority for {0}: {1} {2}'.format(self.torrent_video_file.path, self.torrent_video_file.start_piece_index, self.torrent_video_file.end_piece_index))
                        self.torrent_handle.piece_priority(self.torrent_video_file.start_piece_index, 7)
                        self.torrent_handle.piece_priority(self.torrent_video_file.end_piece_index, 7)

            elif isinstance(alert, libtorrent.torrent_resumed_alert):
                self.bus.log('[Downloader] Torrent resumed')

            # Fallback
            else:                    
                self.bus.log('[Downloader] Unhandled alert received: {0}: {1}'.format(alert.what(), alert.message()))

    ############################################################################
    def _get_video_torrent_file(self):
        video_file = None
        for file in self.torrent_handle.get_torrent_info().files():
            if file.path.endswith('.mkv') or file.path.endswith('.mp4') or file.path.endswith('.avi'):
                if not video_file or video_file.size() < file.size():
                    video_file = file

        return video_file
