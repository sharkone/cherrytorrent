################################################################################
import cherrypy
import datetime
import downloader
import json
import mimetypes
import os
import static
import time

################################################################################
class Server:
    ############################################################################
    def __init__(self, http_config, torrent_config):
        self.http_config    = http_config
        self.torrent_config = torrent_config

        cherrypy.engine.downloader_monitor = downloader.DownloaderMonitor(cherrypy.engine, self.torrent_config)
        cherrypy.engine.downloader_monitor.subscribe()

        self.log_path = os.path.abspath(os.path.join(self.http_config['log_dir'], 'cherrytorrent.log'))
        
    ############################################################################
    def run(self):
        if os.path.isfile(self.log_path):
            os.remove(self.log_path)

        cherrypy.config.update({'log.error_file':self.log_path})
        cherrypy.config.update({'server.socket_host':'0.0.0.0'})
        cherrypy.config.update({'server.socket_port':self.http_config['port']})

        cherrypy.quickstart(ServerRoot(self.log_path))

################################################################################
class ServerRoot:
    ############################################################################
    def __init__(self, log_path):
        self.log_path = log_path

    ############################################################################
    @cherrypy.expose
    def index(self):
        return json.dumps(cherrypy.engine.downloader_monitor.get_status())

    ############################################################################
    @cherrypy.expose
    def log(self):
        result = ''
        with open(self.log_path, 'r') as f:
            for line in iter(f.readline, ''):
                result = result + line + '<br/>'
        
        return result

    ############################################################################
    @cherrypy.expose
    def add(self, uri, download_dir='.'):
        return json.dumps(cherrypy.engine.downloader_monitor.add_torrent(uri, download_dir))

    ############################################################################
    @cherrypy.expose
    def video(self, info_hash):
        if cherrypy.engine.downloader_monitor.is_video_file_ready_from_info_hash(info_hash, True):
            video_file   = cherrypy.engine.downloader_monitor.get_video_file(info_hash)
            content_type = mimetypes.types_map.get(os.path.splitext(video_file.path), None)

            if not content_type:
                if video_file.path.endswith('.avi'):
                    content_type = 'video/avi'
                elif video_file.path.endswith('.mkv'):
                    content_type = 'video/x-matroska'
                elif video_file.path.endswith('.mp4'):
                    content_type = 'video/mp4'

            return static.serve_fileobj(video_file, content_length=video_file.size, content_type=content_type, name=os.path.basename(video_file.path))            
        else:
            time.sleep(2)
            raise cherrypy.HTTPRedirect('/video?info_hash={0}'.format(info_hash), 307)

    ############################################################################
    @cherrypy.expose
    def shutdown(self):
        cherrypy.engine.exit()
        return 'cherrytorrent stopped'
