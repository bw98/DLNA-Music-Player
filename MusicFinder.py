import gi
gi.require_version('GUPnP', '1.2')
gi.require_version('GUPnPAV', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, GObject, GUPnP, GUPnPAV, Gtk

def get_all_available_media_server(timeout=2):

    devices = set()
    loop = GLib.MainLoop()

    def device_available_cb(cp, proxy):
       devices.add(proxy.get_friendly_name())
    
    def loop_quit_cb():
        loop.quit()
        
    ctx = GUPnP.Context.new(None, 0)
    cp = GUPnP.ControlPoint.new(
            ctx, "urn:schemas-upnp-org:device:MediaServer:1")
    cp.connect("device-proxy-available", device_available_cb)
    cp.set_active(True)

    GLib.timeout_add_seconds(timeout, loop_quit_cb)
    loop.run() 

    return devices

class Song:
    def __init__(self, title, album, artist, release_date, genre, duration, size, uri):
        self.title = str(title)
        self.album = str(album)
        self.artist = str(artist)
        self.release_date = str(release_date)
        self.genre = str(genre)
        self.duration = str(duration)
        self.size = str(size)
        self.uri = str(uri)

    def __eq__(self, other):
        if isinstance(other, Song):
            return (self.title == other.title) and (self.album == other.album)
        else:
            return False
    
    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.title) + hash(self.album)

    def __str__(self):
        ret = "title:"
        ret += self.title
        ret += "\nalbum:"
        ret += self.album
        ret += "\nartist:"
        ret += self.artist
        ret += "\nrelease_date:"
        ret += self.release_date
        ret += "\ngenre:"
        ret += self.genre
        ret += "\nduration:"
        ret += self.duration
        ret += "\nsize:"
        ret += self.size
        ret += "\nuri:"
        ret += self.uri
        ret += "\n"
        return ret

class MusicFinder:
    """a class that helps fetch remote music of a target device in the LAN
    """

    def __init__(self, media_server, window): 
        """Initialize UPnP_Finder
        
        :param GLib.MainLoop loop: represent the main event loop of a GTK app
        :param str music_dir: the name of music directory
        :param str media_server: the target media server for searching music
        :param int timeout: the time to quit loop and finish MusicFinder  
        """
        self.media_server = media_server
        # FIXME: need to add multiple lang support for music_dir
        self.music_dir = ["Music", "音乐"]

        self.context = GUPnP.Context.new(None, 0)

        self.control_point = GUPnP.ControlPoint.new(
            self.context, "urn:schemas-upnp-org:device:MediaServer:1")
        self.control_point.connect(
            "device-proxy-available", self._device_proxy_available_cb)
        self.control_point.set_active(True)

        self.window = window

    def _on_browse_ready(self, service, action, data):
        out_name = ["Result", "NumberReturned", "TotalMatches", "UpdateID"]
        out_type = [GObject.TYPE_STRING, GObject.TYPE_STRING, 
                GObject.TYPE_STRING, GObject.TYPE_STRING]

        # retrieve result
        success, return_data = service.end_action_list(action,
                out_name, out_type)

        if not success:
            return
        else:
            if data == "search_music_mode": 
                parser = GUPnPAV.DIDLLiteParser()
                parser.connect(
                    "container-available", self._music_container_found_cb)
                parser.connect("item-available", self._music_item_found_cb)
                parser.parse_didl(return_data[0])
            else:
                parser = GUPnPAV.DIDLLiteParser()
                parser.connect(
                    "container-available", self._container_available_cb)
                parser.parse_didl(return_data[0])

    def _action_browse(self, obj_id="0", data=None):
        in_name = ["ObjectID", "BrowseFlag", "Filter", "StartingIndex", 
                "RequestedCount", "SortCriteria"]
        in_val  = [obj_id, "BrowseDirectChildren", "*", "0", "0", ""]
        
        # non-blocking call
        self.content_directory.begin_action_list(
            "Browse", in_name, in_val, 
            self._on_browse_ready, data)

    def _print_server_info(self, proxy):
        print("-" * 40)
        print(("Name     : %s") % (proxy.get_friendly_name()))
        print(("Location : %s") % (self.content_directory.get_location()))
        print(("udn      : %s") % (self.content_directory.get_udn()))
        print(("type     : %s") % (self.content_directory.get_service_type()))

    def _device_proxy_available_cb(self, cp, proxy, data=None):
        if not(self.media_server == proxy.get_friendly_name()):
            return

        self.content_directory = proxy.get_service(
            "urn:schemas-upnp-org:service:ContentDirectory:1")

        self._action_browse()

    def _container_available_cb(self, parser, obj, data=None):
        if obj.props.child_count > 0:
            if obj.props.title in self.music_dir:
                self._action_browse(obj.props.id, "search_music_mode")
            
    def _music_container_found_cb(self, parser, obj, data=None):
        if obj.props.child_count > 0:
                self._action_browse(obj.props.id, "search_music_mode")

    def _music_item_found_cb(self, parser, obj, data=None):
        resource = obj.get_resources()[0]
        
        song = Song(
            obj.props.title, obj.props.album, obj.props.creator, 
            obj.props.date, obj.props.genre, 
            resource.props.duration, resource.props.size, 
            resource.props.uri)

        self.window.song_set.add(song)

        # update UI for a song in window
        button = Gtk.Button(label=song.title)
        button.connect("clicked", self.window._play_music_cb, song)
        self.window.music_flowbox.add(button)
        
        self.window.music_listbox.show_all()

