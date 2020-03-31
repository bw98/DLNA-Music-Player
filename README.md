# DLNA-Music-Player
A program that supports playing music from remote media devices

### Usage
Typical usage:
>Note! Before using, you need to start the DLNA media server (such as Windows Media Player for Windows) and allow sharing your music directory

```
1. Type `python3 demo.py` in your bash
2. Turn on media device search, all DLNA-enabled devices will be listed
4. Select a device, all music in the music directory of the device will be listed
5. Select a song and play it
```

### Example
[![GQtUtf.gif](https://s1.ax1x.com/2020/03/31/GQtUtf.gif)](https://imgchr.com/i/GQtUtf)

### Technical Details
Use `GUPnP` related framework, which is an elegant, object-oriented open source framework for creating UPnP devices and control points, to detect devices with DLNA media servers in the local area network.

As a DLNA client, this program can register the `browse` event to fetch directory structure in the media server after detecting each device. Then, enter the music directory and recursively query all files in its directory, and update the information of each song on the UI page in async way.

The UI part of the demo is implemented through GTK3.

The two main features of the program `update selectable device list` and `update selectable song list` are asynchronously implemented to avoid unnecessary parameter timeout configuration and blocking waiting.

Use `Gstreamer` to control the playback of a song(uri) from remote media server.
