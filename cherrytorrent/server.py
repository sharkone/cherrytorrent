################################################################################
import cherrypy
import datetime
import downloader
import json
import mimetypes
import os

from cherrypy.lib.static import serve_fileobj

################################################################################
class ConnectionCounterTool(cherrypy.Tool):
    ############################################################################
    def __init__(self):
        cherrypy.Tool.__init__(self, 'before_handler', self._before_handler)
        self.connection_count     = 0
        self.last_connection_time = datetime.datetime.now()

    ############################################################################
    def _setup(self):
        cherrypy.Tool._setup(self)
        cherrypy.serving.request.hooks.attach('on_end_request', self._on_end_request)

    ############################################################################
    def _before_handler(self):
        self.connection_count = self.connection_count + 1

    ############################################################################
    def _on_end_request(self):
        self.connection_count = self.connection_count - 1
        if not self.connection_count:
            self.last_connection_time = datetime.datetime.now()

cherrypy.tools.connection_counter = ConnectionCounterTool()

################################################################################
class InactivityMonitor(cherrypy.process.plugins.Monitor):
    ############################################################################
    def __init__(self, bus, timeout):
        cherrypy.process.plugins.Monitor.__init__(self, bus, self._check_for_timeout, frequency=5)
        self.timeout = timeout

    ############################################################################
    def start(self):
        self.bus.log('[InactivityMonitor] Starting')
        cherrypy.process.plugins.Monitor.start(self)

    ############################################################################
    def stop(self):
        self.bus.log('[InactivityMonitor] Stopping')
        cherrypy.process.plugins.Monitor.stop(self)

    ############################################################################
    def _check_for_timeout(self):
        if not cherrypy.tools.connection_counter.connection_count and (datetime.datetime.now() - cherrypy.tools.connection_counter.last_connection_time) >= datetime.timedelta(seconds=self.timeout):
            self.bus.log('[InactivityMonitor] {0} second timeout exceeded'.format(self.timeout))
            cherrypy.engine.exit()

################################################################################
class Server:
    ############################################################################
    def __init__(self, http_config, torrent_config):
        self.http_config    = http_config
        self.torrent_config = torrent_config

        cherrypy.engine.inactivity_monitor = InactivityMonitor(cherrypy.engine, self.http_config['inactivity_timeout'])
        cherrypy.engine.inactivity_monitor.subscribe()

        cherrypy.engine.downloader_plugin = downloader.DownloaderPlugin(cherrypy.engine, self.torrent_config)
        cherrypy.engine.downloader_plugin.subscribe()
        
    ############################################################################
    def run(self):
        cherrypy.config.update({'server.socket_host':'0.0.0.0'})
        cherrypy.config.update({'server.socket_port':self.http_config['port']})

        cherrypy.quickstart(ServerRoot())

################################################################################
class ServerRoot:
    ############################################################################
    @cherrypy.expose
    @cherrypy.tools.connection_counter()
    def index(self):
        return 'cherrytorrent running'

    ############################################################################
    @cherrypy.expose
    @cherrypy.tools.connection_counter()
    def status(self):
        return json.dumps(cherrypy.engine.downloader_plugin.get_status())

    ############################################################################
    @cherrypy.expose
    @cherrypy.tools.connection_counter()
    def download(self):
        video_file = cherrypy.engine.downloader_plugin.get_video_file()
        if not video_file:
            return 'Not ready!'

        return serve_fileobj(video_file, content_length=video_file.size, content_type='application/x-download', disposition='attachment', name=os.path.basename(video_file.path))

    ############################################################################
    @cherrypy.expose
    @cherrypy.tools.connection_counter()
    def video(self):
        video_file = cherrypy.engine.downloader_plugin.get_video_file()
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

        return serve_fileobj(video_file, content_length=video_file.size, content_type=content_type, name=os.path.basename(video_file.path))

    ############################################################################
    @cherrypy.expose
    def shutdown(self):
        cherrypy.engine.exit()
        return 'cherrytorrent stopped'
