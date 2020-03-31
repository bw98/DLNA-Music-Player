import threading

import gi
gi.require_version('GUPnP', '1.2')
gi.require_version('GUPnPAV', '1.0')
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, GObject, GUPnP, GUPnPAV, Gst, Gtk

from MusicFinder import get_all_available_media_server, Song, MusicFinder

class MyWindow(Gtk.Window):
    """Main window

    To implement three features: 
    1. select a DLNA media device in LAN
    2. list all songs of the device
    3. select a song to play
    """

    def __init__(self):
        super().__init__(title="DLNA Music Player")
        self.set_default_size(800, 600)
        self.connect("destroy", self._main_quit_cb)

        self.devices = set()
        self.update_devs = set()
        self.selected_device_name = ""
        self.song_set = set()
        self.search_state = "No"

        self.box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=30)
        self.add(self.box_outer)
        
        # listbox for DLNA related control widget
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.box_outer.pack_start(listbox, False, True, 0)

        row = Gtk.ListBoxRow()
        box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        search_device_label = Gtk.Label(
            label="Search for DLNA media devices in LAN?", xalign=0)
        switch = Gtk.Switch()
        switch.connect("notify::active", self._on_switch_activated_cb)
        switch.set_active(False)
        box1.pack_start(search_device_label, True, True, 0)
        box1.pack_start(switch, False, True ,0)
        row.add(box1)
        listbox.add(row)

        # server_listbox for all available media server widgets
        self.server_listbox = None
        # music_box for all music in a selected server
        self.music_listbox = None

        self.show_all()

    def _main_quit_cb(self, window_obj):
        self.destroy()
        Gtk.main_quit()


    def _update_all_available_media_server(self):

        def search_devs():
            loop = GLib.MainLoop()

            def device_available_cb(cp, proxy):
                self.update_devs.add(proxy.get_friendly_name())

            def check_search_state_cb():
                if self.search_state == "No":
                    loop.quit()
                    return False
                
                return True

            ctx = GUPnP.Context.new(None, 0)
            cp = GUPnP.ControlPoint.new(
                    ctx, "urn:schemas-upnp-org:device:MediaServer:1")
            cp.connect("device-proxy-available", device_available_cb)
            cp.set_active(True)

            # FIXME: Thread unsafe
            # If change the `search_state` too fast, the function
            # `check_search_state_cb` cannot be detected, and eventually
            # the old thread will remain
            GLib.timeout_add_seconds(2, check_search_state_cb)
            loop.run()

        def update_devs_cb():
            if self.search_state == "No":
                return False

            new_devs = self.update_devs - self.devices
            if len(new_devs) > 0 and self.server_listbox is not None:
                for new_dev in new_devs:
                    self.devices.add(new_dev)
                    row = Gtk.ListBoxRow()
                    button = Gtk.Button(label=new_dev)
                    button.connect("clicked", self._search_music_cb)
                    row.add(button)
                    self.server_listbox.add(row)

                self.server_listbox.show_all()
                
            return True  # set `True` so as to invoke this function next time

        thread = threading.Thread(target=search_devs)
        thread.setDaemon(True)
        thread.start()

        # FIXME: Thread unsafe
        GLib.timeout_add_seconds(5, update_devs_cb)  # update devics per 5 sec

    def _on_switch_activated_cb(self, switch, data):
        if switch.get_active():
            self.search_state = "Yes"

            self.devices = get_all_available_media_server(timeout=1)

            self._update_all_available_media_server()

            self._show_server_list()
        else:
            self.search_state = "No"
            self.devices.clear()
            self.selected_device_name = ""
            self.song_set.clear()

            if self.server_listbox is not None:
                self._close_server_list()

            if self.music_listbox is not None:
                self._close_music_list()
                
    def _show_server_list(self):
        self.server_listbox = Gtk.ListBox()
        self.server_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.box_outer.pack_start(self.server_listbox, False, True, 0)

        list_title = Gtk.Label(
                label="Available DLNA Media Server", xalign=0)
        self.server_listbox.add(list_title)

        for dev in self.devices:
            row = Gtk.ListBoxRow()
            button = Gtk.Button(label=dev)
            button.connect("clicked", self._search_music_cb)
            row.add(button)
            self.server_listbox.add(row)

        self.server_listbox.show_all()

    def _close_server_list(self):
        self.server_listbox.destroy()
        self.server_listbox = None

    def _search_music_cb(self, button_obj):
        if self.selected_device_name == button_obj.get_label():
            return

        self.selected_device_name = button_obj.get_label()

        # need to reload music list when clicking on a new server
        if self.music_listbox is not None:
            self.song_set.clear()
            self._close_music_list()

        # create music list UI, wait for MusicFinder to update UI
        self._create_music_list()
        
        #search and update music in music list
        finder = MusicFinder(button_obj.get_label(), self)

    def _create_music_list(self):
        # music_box for all music in a selected server
        self.music_listbox = Gtk.ListBox()
        self.box_outer.pack_start(self.music_listbox, False, True, 0)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.music_listbox.add(box)

        box_title = Gtk.Label(
                label="Click One Song to Play", xalign=0)
        box.add(box_title)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.ALWAYS)
        sw.set_min_content_height(300)
        sw.set_min_content_width(150)
        box.pack_start(sw, True, True, 0)

        self.music_flowbox = Gtk.FlowBox()
        self.music_flowbox.set_valign(Gtk.Align.START)
        self.music_flowbox.set_max_children_per_line(1)
        self.music_flowbox .set_selection_mode(Gtk.SelectionMode.NONE)
        sw.add(self.music_flowbox)

        self.music_listbox.show_all()

    def _close_music_list(self):
        self.music_listbox.destroy()
        self.music_listbox = None

    def _play_music_cb(self, button_obj, song):
        mwin = MusicWindow(song)
        
class MusicWindow(Gtk.Window):

    def __init__(self, song):
        super().__init__(title="Music Player")
        self.set_title("Music Player")
        self.set_default_size(500, 100)
        self.connect("delete-event", self._on_delete)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.box)

        title_label = Gtk.Label(label="Title: "+song.title, xalign=0)
        album_label = Gtk.Label(label="Album: "+song.album, xalign=0)
        artist_label = Gtk.Label(label="Artist: "+song.artist, xalign=0)
        date_label = Gtk.Label(
                label="Relase Date: "+song.release_date, xalign=0)
        genre_label = Gtk.Label(label="Genre: "+song.genre, xalign=0)
        duration_label = Gtk.Label(label="Duration: "+song.duration, xalign=0)
        
        button = Gtk.Button(label="Start Play")
        button.connect("clicked", self._start_stop, song.uri)

        self.box.pack_start(title_label, False, True, 0)
        self.box.pack_start(album_label, False, True, 0)
        self.box.pack_start(artist_label, False, True, 0)
        self.box.pack_start(date_label, False, True, 0)
        self.box.pack_start(genre_label, False, True, 0)
        self.box.pack_start(duration_label, False, True, 0)

        self.box.pack_start(button, False, True, 0)
        
        self.player = Gst.ElementFactory.make("playbin", "player")
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)
        
        self.show_all()

    def _on_delete(self, window_obj, data):
        self.hide()
        # destroy box, including  music label, play-stop button
        self.box.destroy()
        # free music resources of player
        self.player.set_state(Gst.State.NULL)
        self.player.unref()

        return False # job completed

    def _start_stop(self, button_obj, uri):
        if button_obj.get_label() == "Start Play":
            self.player.set_property("uri", uri)
            self.player.set_state(Gst.State.PLAYING)

    def _on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
            self.button.set_label("Start Play")
        elif t == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print("Error: %s" % err, debug)
            self.button.set_label("Start Play")

if __name__ == "__main__":
    win = MyWindow()
    Gst.init(None)
    Gtk.main()

