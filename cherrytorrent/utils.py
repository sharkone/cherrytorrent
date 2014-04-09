################################################################################
import math

################################################################################
PRELOAD_RATIO  = 0.005

################################################################################
def piece_from_offset(torrent_handle, offset):
    return offset / torrent_handle.get_torrent_info().piece_length()

################################################################################
def get_preload_buffer_piece_count(torrent_video_file):
    piece_count     = max(1, torrent_video_file.end_piece_index - torrent_video_file.start_piece_index)
    high_prio_count = min(piece_count, int(math.ceil(piece_count * PRELOAD_RATIO)))
    return high_prio_count
