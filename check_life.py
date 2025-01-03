from datetime import datetime

def is_valid(note: object) -> bool:
    if datetime.now() >= note.dead_line:
            note.delete()
            return False
    elif note.deletion_on_first_reading == True and note.read_count > 0:
            return False
    return True