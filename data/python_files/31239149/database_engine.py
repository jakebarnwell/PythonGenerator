import sqlite3
_connection = None

def Get_DatabaseConnection():
    global _connection
    if not _connection:
        _connection = sqlite3.Connection('sitedatabase.db')
    return _connection

def Init_Database():
    conn = Get_DatabaseConnection()
    curs = conn.cursor()
    curs.execute("SELECT * FROM sqlite_master WHERE type='table';")
    tablenames = {}
    for entry in curs:
        tablenames[entry[1]] = 0

    conn.close()
    #check that all the tables that should be there are there.
    if "photos" not in tablenames:
        print "ERROR: Missing Table 'photos'"
        import create_database_tables
    elif "photo_comments" not in tablenames:
        print "ERROR Missing Table 'photo_comments'"
        import create_database_tables
    elif "users" not in tablenames:
        print "ERROR Missing Table 'users'"
        import create_database_tables
    elif "friends" not in tablenames:
        print "ERROR Missing Table 'friends'"
        import create_database_tables
    elif "events" not in tablenames:
        print "ERROR Missing Table 'events'"
        import create_database_tables
    elif "sessions" not in tablenames:
        print "ERROR Missing Table 'sessions'"
        import create_database_tables
    elif "eventtags" not in tablenames:
        print "ERROR Missing Table 'eventtags'"
        import create_database_tables
    global _connection
    _connection = sqlite3.Connection('sitedatabase.db')
    
        
    


