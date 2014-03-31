################################################################################
import io
import os
import time
import utils

################################################################################
class FileWrapper(io.RawIOBase):
    ############################################################################
    def __init__(self, torrent_handle, torrent_file):
        self.torrent_handle = torrent_handle
        self.torrent_file   = torrent_file

        self.path = os.path.join(self.torrent_handle.save_path(), torrent_file.path)
        self.size = torrent_file.size

        while not os.path.isfile(self.path):
            time.sleep(0.1)

        self.file = open(self.path, 'rb')

    ############################################################################
    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            new_position = offset
        elif whence == io.SEEK_CUR:
            new_position = self.file.tell() + offset
        elif whence == io.SEEK_END:
            new_position = self.size + offset

        piece_index = utils.piece_from_offset(self.torrent_handle, self.torrent_file.offset + new_position)
        self._wait_for_piece(piece_index)
        return self.file.seek(offset, whence)
        
    ############################################################################
    def read(self, size=-1):
        current_offset = self.file.tell()

        if size == -1:
            size = self.size - current_offset
        
        if size <= self.torrent_handle.get_torrent_info().piece_length():
            piece_index = utils.piece_from_offset(self.torrent_handle, self.torrent_file.offset + current_offset + size)
            self._wait_for_piece(piece_index)
            return self.file.read(size) 

        #print 'Reading more than one piece...'
        # TODO: Should wait/read piece one by one and concat result
        return self.file.read(size)

    ############################################################################
    def close(self):
        return self.file.close()

    ############################################################################
    def _wait_for_piece(self, piece_index):
        #print 'Waiting for piece: {0}'.format(piece_index)
        while not self.torrent_handle.have_piece(piece_index):
            time.sleep(0.1)
