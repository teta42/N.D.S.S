from datetime import datetime

def is_valid(note: object) -> bool:
    if datetime.now() >= note.dead_line:
            note.delete()
            return False
    return True