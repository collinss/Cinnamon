from gi.repository import Gio, GObject
from SettingsWidgets import *
import collections
import json

JSON_SETTINGS_PROPERTIES_MAP = {
    "min"           : "mini",
    "max"           : "maxi",
    "step"          : "step",
    "units"         : "units",
    "select-dir"    : "dir_select",
    "height"        : "height",
    "tooltip"       : "tooltip",
    "possible"      : "possible",
    "dependency"    : "dep_key"
}

class JSONSettingsHandler(object):
    def __init__(self, filepath, notify_callback=None):
        super(JSONSettingsHandler, self).__init__()

        self.resume_timeout = None
        self.notify_callback = notify_callback
        
        self.filepath = filepath
        self.file_obj = Gio.File.new_for_path(self.filepath)
        self.file_monitor = self.file_obj.monitor_file(Gio.FileMonitorFlags.SEND_MOVED, None)
        self.file_monitor.connect("changed", self.check_settings)

        self.bindings = {}
        self.listeners = {}
        self.deps = {}

        self.settings = self.get_settings()

    def bind(self, key, obj, prop, direction, map_get=None, map_set=None):
        binding_info = {"obj": obj, "prop": prop, "dir": direction, "map_get": map_get, "map_set": map_set}
        if key not in self.bindings:
            self.bindings[key] = []
        self.bindings[key].append(binding_info)
        if direction in [Gio.SettingsBindFlags.DEFAULT, Gio.SettingsBindFlags.GET]:
            self.set_object_value(binding_info, self.get_value(key))
        if direction in [Gio.SettingsBindFlags.DEFAULT, Gio.SettingsBindFlags.SET]:
            binding_info["oid"] = obj.connect("notify::"+prop, self.object_value_changed, key)

    def listen(self, key, callback):
        self.listeners[key] = callback

    def get_value(self, key):
        return self.get_property(key, "value")

    def set_value(self, key, value):
        if value != self.settings[key]["value"]:
            self.settings[key]["value"] = value
            self.save_settings()
            if self.notify_callback:
                self.notify_callback(self, key)

    def get_property(self, key, prop):
        props = self.settings[key]
        return props[prop]

    def has_property(self, key, prop):
        return prop in self.settings.keys()

    def object_value_changed(self, obj, value, key):
        for info in self.bindings[key]:
            if obj == info["obj"]:
                value = info["obj"].get_property(info["prop"])
                if "map_set" in info.keys() and info["map_set"] != None:
                    value = info["map_set"](value)
            else:
                self.set_object_value(info, value)
        self.set_value(key, value)

    def set_object_value(self, info, value):
        if info["dir"] not in [Gio.SettingsBindFlags.DEFAULT, Gio.SettingsBindFlags.GET]:
            return

        with info["obj"].freeze_notify():
            if "map_get" in info.keys() and info["map_get"] != None:
                value = info["map_get"](value)
            if value != info["obj"].get_property(info["prop"]):
                info["obj"].set_property(info["prop"], value)

    def check_settings(self, *args):
        old_settings = self.settings
        self.settings = self.get_settings()

        for key in self.bindings:
            new_value = self.settings[key]["value"]
            if new_value != old_settings[key]["value"]:
                for info in self.bindings[key]:
                    self.set_object_value(info, new_value)

        for key, callback in self.listeners.items():
            new_value = self.settings[key]["value"]
            if new_value != old_settings[key]["value"]:
                callback(key, new_value)

    def get_settings(self):
        raw_data = open(self.filepath).read()
        try:
            settings = json.loads(raw_data, encoding=None, object_pairs_hook=collections.OrderedDict)
        except:
            raise Exception("Failed to parse settings JSON data for file %s" % (self.filepath))
        return settings

    def save_settings(self):
        self.pause_monitor()
        if os.path.exists(self.filepath):
            os.remove(self.filepath)
        raw_data = json.dumps(self.settings, indent=4)
        new_file = open(self.filepath, 'w+')
        new_file.write(raw_data)
        self.resume_monitor()

    def pause_monitor(self):
        self.file_monitor.cancel()
        self.handler = None

    def resume_monitor(self):
        if self.resume_timeout:
            GObject.source_remove(self.resume_timeout)
        self.resume_timeout = GObject.timeout_add(2000, self.do_resume)

    def do_resume(self):
        self.file_monitor = self.file_obj.monitor_file(Gio.FileMonitorFlags.SEND_MOVED, None)
        self.handler = self.file_monitor.connect("changed", self.check_settings)
        self.resume_timeout = None
        return False

class JSONSettingsBackend(object):
    def attach(self):
        if hasattr(self, "set_rounding") and self.settings.has_property(self.key, "round"):
            self.set_rounding(self.settings.get_property(self.key, "round"))
        if hasattr(self, "bind_object"):
            bind_object = self.bind_object
        else:
            bind_object = self.content_widget
        if self.bind_dir != None:
            self.settings.bind(self.key, bind_object, self.bind_prop, self.bind_dir,
                               self.map_get if hasattr(self, "map_get") else None,
                               self.map_set if hasattr(self, "map_set") else None)
        else:
            self.settings.listen(self.key, self.on_setting_changed)
            self.on_setting_changed()

    def set_value(self, value):
        self.settings.set_value(self.key, value)

    def get_value(self):
        return self.settings.get_value(self.key)

    def get_range(self):
        min = self.settings.get_property(self.key, "min")
        max = self.settings.get_property(self.key, "max")
        return [min, max]

def json_settings_factory(subclass):
    class NewClass(globals()[subclass], JSONSettingsBackend):
        def __init__(self, key, settings, properties):
            self.key = key
            self.settings = settings
            
            kwargs = {}
            for prop in properties:
                if prop in JSON_SETTINGS_PROPERTIES_MAP:
                    kwargs[JSON_SETTINGS_PROPERTIES_MAP[prop]] = properties[prop]
                elif prop == "options":
                    kwargs["options"] = []
                    for value, label in properties[prop].items():
                        kwargs["options"].append((label, value))
            super(NewClass, self).__init__(properties["description"], **kwargs)
            self.attach()

        def set_dep_key(self, dep_key):
            self.settings.bind(dep_key, self, "sensitive", Gio.SettingsBindFlags.GET)

    return NewClass

for widget in CAN_BACKEND:
    globals()["JSONSettings"+widget] = json_settings_factory(widget)
