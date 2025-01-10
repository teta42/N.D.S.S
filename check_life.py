from datetime import datetime

def is_valid(note: object, user:bool) -> bool:
    if datetime.now() >= note.dead_line:
            note.delete()
            return False
    elif note.deletion_on_first_reading == True and note.read_count > 0:
            note.delete()
            return False
    elif note.only_authorized and not user:
        return False
            
    return True

#TODO Дорабатывать 