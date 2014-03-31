################################################################################
def piece_from_offset(torrent_handle, offset):
    return offset / torrent_handle.get_torrent_info().piece_length()
