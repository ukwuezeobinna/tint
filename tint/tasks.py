from tint.tint.quota import validate_files_space_limit, validate_db_space_limit

def daily():
    validate_files_space_limit()
    validate_db_space_limit()