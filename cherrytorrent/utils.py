################################################################################
def piece_from_offset(torrent_handle, offset):
    piece_length = torrent_handle.get_torrent_info().piece_length()
    piece_index  = offset / piece_length
    piece_offset = offset % piece_length
    return piece_index, piece_offset
