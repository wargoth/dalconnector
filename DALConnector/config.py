# Once you've loaded a song, do you want DAL Connector to periodically check for new saves?
# I.e., you've loaded song 8.  Now it will watch for 8b.  Then 8c.  Then 8d.
# If it finds one, it will try to load it
WATCH_FOR_NEW_SAVES = True   # True or False

# If we're watching for new saves, when do we give up?  If one doesn't appear in X seconds, assume one isn't coming
NEW_SAVE_SLEEP_TIMER = 600  # Integer seconds (10 minutes)

