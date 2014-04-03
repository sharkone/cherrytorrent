################################################################################
import cherrypy
import datetime
import downloader
import json
import mimetypes
import os
import static

################################################################################
class InactivityMonitor(cherrypy.process.plugins.Monitor):
    ############################################################################
    def __init__(self, bus, timeout):
        cherrypy.process.plugins.Monitor.__init__(self, bus, self._check_for_timeout, frequency=1)
        self.timeout                 = timeout
        self.active_connection_count = 0
        self.update_last_connection_time()

    ############################################################################
    def start(self):
        cherrypy.process.plugins.Monitor.start(self)

    ############################################################################
    def stop(self):
        cherrypy.process.plugins.Monitor.stop(self)

    ############################################################################
    def update_last_connection_time(self):
        self.last_connection_time = datetime.datetime.now()

    ############################################################################
    def _check_for_timeout(self):
        prev_active_connection_count = self.active_connection_count

        self.active_connection_count = 0
        for thread in cherrypy.server.httpserver.requests._threads:
            if thread.conn:
                self.active_connection_count = self.active_connection_count + 1

        if prev_active_connection_count > 0 and self.active_connection_count == 0:
            self.update_last_connection_time()

        if self.active_connection_count == 0 and (datetime.datetime.now() - self.last_connection_time) >= datetime.timedelta(seconds=self.timeout):
            if cherrypy.engine.state == cherrypy.engine.states.STARTED:
                self.bus.log('{0} seconds inactivity timeout exceeded'.format(self.timeout))
                cherrypy.engine.exit()

################################################################################
class Server:
    ############################################################################
    def __init__(self, http_config, torrent_config):
        self.http_config    = http_config
        self.torrent_config = torrent_config

        cherrypy.engine.inactivity_monitor = InactivityMonitor(cherrypy.engine, self.http_config['inactivity_timeout'])
        cherrypy.engine.inactivity_monitor.subscribe()

        cherrypy.engine.downloader_monitor = downloader.DownloaderMonitor(cherrypy.engine, self.torrent_config)
        cherrypy.engine.downloader_monitor.subscribe()
        
    ############################################################################
    def run(self):
        cherrypy.config.update({'server.socket_host':'0.0.0.0'})
        cherrypy.config.update({'server.socket_port':self.http_config['port']})

        cherrypy.quickstart(ServerRoot())

################################################################################
class ServerRoot:
    ############################################################################
    @cherrypy.expose
    def index(self):
        cherrypy.engine.inactivity_monitor.update_last_connection_time()
        return 'cherrytorrent running'

    ############################################################################
    @cherrypy.expose
    def status(self):
        cherrypy.engine.inactivity_monitor.update_last_connection_time()
        return json.dumps(cherrypy.engine.downloader_monitor.get_status())

    ############################################################################
    @cherrypy.expose
    def download(self):
        cherrypy.engine.inactivity_monitor.update_last_connection_time()
        
        video_file = cherrypy.engine.downloader_monitor.get_video_file()
        if not video_file:
            return 'Not ready!'

        return static.serve_fileobj(video_file, content_length=video_file.size, content_type='application/x-download', disposition='attachment', name=os.path.basename(video_file.path))

    ############################################################################
    @cherrypy.expose
    def video(self):
        cherrypy.engine.inactivity_monitor.update_last_connection_time()

        video_file = cherrypy.engine.downloader_monitor.get_video_file()
        if not video_file:
            return 'Not ready!'

        content_type = mimetypes.types_map.get(os.path.splitext(video_file.path), None)
        
        if not content_type:
            if video_file.path.endswith('.avi'):
                content_type = 'video/avi'
            elif video_file.path.endswith('.mkv'):
                content_type = 'video/x-matroska'
            elif video_file.path.endswith('.mp4'):
                content_type = 'video/mp4'

        return static.serve_fileobj(video_file, content_length=video_file.size, content_type=content_type, name=os.path.basename(video_file.path))

    ############################################################################
    @cherrypy.expose
    def shutdown(self):
        cherrypy.engine.exit()
        return 'cherrytorrent stopped'
