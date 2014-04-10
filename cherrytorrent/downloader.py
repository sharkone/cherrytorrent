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
        self.thread_running     = False

    ############################################################################
    def start(self):
        cherrypy.process.plugins.Monitor.start(self)

        self.bus.log('[Downloader] Starting session')
        self.session = libtorrent.session()
        self.session.set_alert_mask(libtorrent.alert.category_t.error_notification | libtorrent.alert.category_t.status_notification | libtorrent.alert.category_t.storage_notification)
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
            remove_torrent_flags = libtorrent.options_t.delete_files if not self.torrent_config['keep_files'] else 0
            self.session.remove_torrent(self.torrent_handle, remove_torrent_flags)

        while self.torrent_handle:
            time.sleep(0.1)

        self.session.stop_natpmp()
        self.session.stop_upnp()
        self.session.stop_lsd()
        self.session.stop_dht()

        self.thread_running = False
        time.sleep(1)
        cherrypy.process.plugins.Monitor.stop(self)

    ############################################################################
    def get_status(self):
        result = {}

        if self.torrent_handle:
            status = self.torrent_handle.status()
            result['session']                  = {}
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
            result['video_file']                          = {}
            result['video_file']['path']                  = self.torrent_video_file.path
            result['video_file']['size']                  = self.torrent_video_file.size
            result['video_file']['start_piece_index']     = self.torrent_video_file.start_piece_index
            result['video_file']['end_piece_index']       = self.torrent_video_file.end_piece_index
            result['video_file']['total_pieces']          = self._get_video_file_total_pieces(self.torrent_video_file)
            result['video_file']['preload_buffer_pieces'] = utils.get_preload_buffer_piece_count(self.torrent_video_file)
            result['video_file']['is_ready_fast']         = self.is_video_file_ready(True, False)
            result['video_file']['is_ready_slow']         = self.is_video_file_ready(False, False)
            result['video_file']['complete_pieces']       = self._get_video_file_complete_pieces(self.torrent_handle, self.torrent_video_file)

            piece_map = ''
            for piece_index in range(self.torrent_video_file.start_piece_index, self.torrent_video_file.end_piece_index + 1):
                if self.torrent_handle.have_piece(piece_index):
                    piece_map = piece_map + '*'
                elif self.torrent_handle.piece_priority(piece_index) == 0:
                    piece_map = piece_map + '0'
                elif self.torrent_handle.piece_priority(piece_index) == 7:
                    piece_map = piece_map + '7'
                else:
                    piece_map = piece_map + '.'
            result['video_file']['piece_map'] = piece_map

        return result

    ############################################################################
    def is_video_file_ready(self, is_fast, log_enabled=True):
        if self.torrent_handle:
            status = self.torrent_handle.status()
            if int(status.state) >= 3 and self.torrent_video_file:
                complete_pieces = self._get_video_file_complete_pieces(self.torrent_handle, self.torrent_video_file)
                total_pieces    = self._get_video_file_total_pieces(self.torrent_video_file)
                needed_pieces   = utils.get_preload_buffer_piece_count(self.torrent_video_file)#int(math.ceil(total_pieces * 0.05))

                if is_fast or complete_pieces >= needed_pieces:
                    return True
                else:
                    if log_enabled:
                        self.bus.log('[Downloader] Not enough pieces yet: {0}/{1} (total: {2}) @ {3} kB/s'.format(complete_pieces, needed_pieces, total_pieces, status.download_rate / 1024))
            else:
                if log_enabled:
                    self.bus.log('[Downloader] Not ready yet: {0}'.format(str(status.state)))
        else:
            if log_enabled:
                self.bus.log('[Downloader] Not ready yet')

        return False

    ############################################################################
    def get_video_file(self):
        if self.torrent_video_file:
            return filewrapper.FileWrapper(self.bus, self.torrent_handle, self.torrent_video_file)

    ############################################################################
    def _background_task(self):
        self.thread_running = True

        while not self.session and self.thread_running:
            time.sleep(0.1)

        while self.thread_running:
            self.session.wait_for_alert(1000)
            alert = self.session.pop_alert()
            if alert:
                # Critical alerts
                if isinstance(alert, libtorrent.torrent_error_alert):
                    self.bus.log('[Downloader] {0}: {1}'.format(alert.what(), alert.message()))
                    self.torrent_handle = None
                    cherrypy.engine.exit()
                
                # Ignored alerts
                elif isinstance(alert, libtorrent.portmap_error_alert):
                    pass
                elif isinstance(alert, libtorrent.external_ip_alert):
                    pass
                elif isinstance(alert, libtorrent.add_torrent_alert):
                   pass
                elif isinstance(alert, libtorrent.torrent_checked_alert):
                   pass
                elif isinstance(alert, libtorrent.hash_failed_alert):
                   pass
                elif isinstance(alert, libtorrent.tracker_error_alert):
                    pass
                elif alert.what() == 'cache_flushed_alert':
                    # TODO: Need to fix python bindings to properly expose this alert
                    pass

                # Session alerts
                elif isinstance(alert, libtorrent.listen_succeeded_alert):
                    # TODO: Need to fix python bindings to properly expose endpoint as tuple
                    self.bus.log('[Downloader] Session {0}'.format(alert.message()))

                # Torrent alerts
                elif isinstance(alert, libtorrent.torrent_added_alert):
                    self.bus.log('[Downloader] Torrent added')
                    self.torrent_handle = alert.handle
                    self.torrent_handle.set_sequential_download(True)
                elif isinstance(alert, libtorrent.torrent_removed_alert):
                    self.bus.log('[Downloader] Torrent removed')
                    self.torrent_handle = self.torrent_handle if not self.torrent_config['keep_files'] else None
                elif isinstance(alert, libtorrent.torrent_resumed_alert):
                    self.bus.log('[Downloader] Torrent resumed')

                elif isinstance(alert, libtorrent.torrent_deleted_alert):
                    self.bus.log('[Downloader] Torrent files deleted')
                    self.torrent_handle = None
                elif isinstance(alert, libtorrent.torrent_delete_failed_alert):
                    self.bus.log('[Downloader] Torrent files deletion failed')
                    self.torrent_handle = None

                elif isinstance(alert, libtorrent.metadata_received_alert):
                    self.bus.log('[Downloader] Torrent metadata received')
                    self.torrent_video_file = self._get_video_torrent_file()
                    if self.torrent_video_file:
                        self.torrent_video_file.start_piece_index = utils.piece_from_offset(self.torrent_handle, self.torrent_video_file.offset)
                        self.torrent_video_file.end_piece_index   = utils.piece_from_offset(self.torrent_handle, self.torrent_video_file.offset + self.torrent_video_file.size)
                    else:
                        self.bus.log('[Downloader] No video file found')
                        cherrypy.engine.exit()

                elif isinstance(alert, libtorrent.state_changed_alert):
                    self.bus.log('[Downloader] Torrent state changed: {0}'.format(alert.state))

                # Fallback
                else:                    
                    self.bus.log('[Downloader] Unhandled alert received: {0}: {1}'.format(alert.what(), alert.message()))

    ############################################################################
    def _get_video_torrent_file(self):
        video_file = None
        for file in self.torrent_handle.get_torrent_info().files():
            if file.path.endswith('.mkv') or file.path.endswith('.mp4') or file.path.endswith('.avi'):
                if not video_file or video_file.size < file.size:
                    video_file = file

        return video_file

    ############################################################################
    def _get_video_file_total_pieces(self, torrent_video_file):
        return max(1, self.torrent_video_file.end_piece_index - self.torrent_video_file.start_piece_index)

    ############################################################################
    def _get_video_file_complete_pieces(self, torrent_handle, torrent_video_file):
        complete_pieces = 0

        if not torrent_video_file:
            return 0

        for piece_index in range(torrent_video_file.start_piece_index, torrent_video_file.end_piece_index + 1):
            if torrent_handle.have_piece(piece_index):
                complete_pieces = complete_pieces + 1
            else:
                break

        return complete_pieces
