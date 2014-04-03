################################################################################
PRELOAD_BUFFER = 5 * 1024 * 1024

################################################################################
def piece_from_offset(torrent_handle, offset):
    return offset / torrent_handle.get_torrent_info().piece_length()

################################################################################
def set_piece_priorities(torrent_handle, torrent_video_file, start_piece_index, rollback):
    piece_count     = max(1, torrent_video_file.end_piece_index - torrent_video_file.start_piece_index)
    high_prio_count = min((min(PRELOAD_BUFFER, torrent_video_file.size) * piece_count) / torrent_video_file.size, piece_count)

    if not rollback:
        if (start_piece_index + high_prio_count) > piece_count:
            high_prio_count = piece_count - start_piece_index

        for i in range(0, high_prio_count):
            torrent_handle.piece_priority(start_piece_index + i, 7)
    else:
        if (start_piece_index - high_prio_count) < 0:
            high_prio_count = start_piece_index

        for i in range(0, high_prio_count):
            torrent_handle.piece_priority(start_piece_index - i, 7)
