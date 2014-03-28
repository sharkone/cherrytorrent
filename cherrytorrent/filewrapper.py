################################################################################
import io
import os
import time

################################################################################
VIRTUAL_READ_THRESHOLD = 100 * 1024

################################################################################
class FileWrapper(io.RawIOBase):
    def __init__(self, torrent_handle, torrent_file):
        self.torrent_handle = torrent_handle
        self.torrent_file   = torrent_file

        self.path = os.path.join(self.torrent_handle.save_path(), torrent_file.path)
        self.size = torrent_file.size

        while not os.path.isfile(self.path) or os.path.getsize(self.path) != self.size:
            time.sleep(0.1)

        self.file         = open(self.path, 'rb')
        self.virtual_read = False

    def fileno(self):
        return self.file.fileno()

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            new_position = offset
        elif whence == io.SEEK_CUR:
            new_position = self.file.tell() + offset
        elif whence == io.SEEK_END:
            new_position = self.size + offset

        if (self.size - new_position) < self.torrent_handle.get_torrent_info().piece_length():
            self.virtual_read = True
            return

        piece_index, piece_offset = self._piece_from_offset(new_position)
        self._wait_for_piece(piece_index)
        return self.file.seek(offset, whence)
        
    def read(self, size=-1):
        if self.virtual_read:
            self.virtual_read = False
            return ""

        current_offset = self.file.tell()

        if size == -1:
            size = self.size - current_offset
        
        if size <= self.torrent_handle.get_torrent_info().piece_length():
            piece_index, piece_offset = self._piece_from_offset(current_offset + size)
            self._wait_for_piece(piece_index)
            return self.file.read(size) 

        print 'Reading more than one piece...'
        # TODO: Should wait/read piece one by one and concat result
        return self.file.read(size)

    def close(self):
        return self.file.close()

    def _piece_from_offset(self, offset):
        piece_length = self.torrent_handle.get_torrent_info().piece_length()
        piece_index  = (self.torrent_file.offset + offset) / piece_length
        piece_offset = (self.torrent_file.offset + offset) % piece_length
        return piece_index, piece_offset

    def _wait_for_piece(self, piece_index):
        while not self.torrent_handle.have_piece(piece_index):
            time.sleep(0.1)
