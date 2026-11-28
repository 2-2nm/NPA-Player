from enum import IntEnum


class Page(IntEnum):
    """Index of each page in the main stack (also what the sidebar emits)."""
    LIBRARY = 0
    PLAYER = 1
    PLAYLISTS = 2
    COLLECTION = 3   # one playlist or smart collection
    FOLDERS = 4      # music / lyrics folders
    SETTINGS = 5