from gi.repository import Gio, GLib
from SettingsWidgets import *

# Monkey patch Gio.Settings object
def __setitem__(self, key, value):
    # set_value() aborts the program on an unknown key
    if key not in self:
        raise KeyError('unknown key: %r' % (key,))

    # determine type string of this key
    range = self.get_range(key)
    type_ = range.get_child_value(0).get_string()
    v = range.get_child_value(1)
    if type_ == 'type':
        # v is boxed empty array, type of its elements is the allowed value type
        assert v.get_child_value(0).get_type_string().startswith('a')
        type_str = v.get_child_value(0).get_type_string()[1:]
    elif type_ == 'enum':
        # v is an array with the allowed values
        assert v.get_child_value(0).get_type_string().startswith('a')
        type_str = v.get_child_value(0).get_child_value(0).get_type_string()
    elif type_ == 'flags':
        # v is an array with the allowed values
        assert v.get_child_value(0).get_type_string().startswith('a')
        type_str = v.get_child_value(0).get_type_string()
    elif type_ == 'range':
        # type_str is a tuple giving the range
        assert v.get_child_value(0).get_type_string().startswith('(')
        type_str = v.get_child_value(0).get_type_string()[1]

    if not self.set_value(key, GLib.Variant(type_str, value)):
        raise ValueError("value '%s' for key '%s' is outside of valid range" % (value, key))

def bind_with_mapping(self, key, widget, prop, flags, key_to_prop, prop_to_key):
    self._ignore_key_changed = False

    def key_changed(settings, key):
        if self._ignore_key_changed:
            return
        self._ignore_prop_changed = True
        widget.set_property(prop, key_to_prop(self[key]))
        self._ignore_prop_changed = False

    def prop_changed(widget, param):
        if self._ignore_prop_changed:
            return
        self._ignore_key_changed = True
        self[key] = prop_to_key(widget.get_property(prop))
        self._ignore_key_changed = False

    if not (flags & (Gio.SettingsBindFlags.SET | Gio.SettingsBindFlags.GET)): # ie Gio.SettingsBindFlags.DEFAULT
       flags |= Gio.SettingsBindFlags.SET | Gio.SettingsBindFlags.GET
    if flags & Gio.SettingsBindFlags.GET:
        key_changed(self, key)
        if not (flags & Gio.SettingsBindFlags.GET_NO_CHANGES):
            self.connect('changed::' + key, key_changed)
    if flags & Gio.SettingsBindFlags.SET:
        widget.connect('notify::' + prop, prop_changed)
    if not (flags & Gio.SettingsBindFlags.NO_SENSITIVITY):
        self.bind_writable(key, widget, "sensitive", False)

Gio.Settings.bind_with_mapping = bind_with_mapping
Gio.Settings.__setitem__ = __setitem__

class DependencyCheckInstallButton(Gtk.Box):
    def __init__(self, checking_text, install_button_text, packages, final_widget=None, satisfied_cb=None):
        super(DependencyCheckInstallButton, self).__init__(orientation=Gtk.Orientation.HORIZONTAL)

        self.packages = packages
        self.satisfied_cb = satisfied_cb

        self.checking_text = checking_text
        self.install_button_text = install_button_text

        self.stack = Gtk.Stack()
        self.pack_start(self.stack, False, False, 0)

        self.progress_bar = Gtk.ProgressBar()
        self.stack.add_named(self.progress_bar, "progress")

        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text(self.checking_text)

        self.install_button = Gtk.Button(install_button_text)
        self.install_button.connect("clicked", self.on_install_clicked)
        self.stack.add_named(self.install_button, "install")

        if final_widget:
            self.stack.add_named(final_widget, "final")
        else:
            self.stack.add_named(Gtk.Alignment(), "final")

        self.stack.set_visible_child_name("progress")

        self.progress_source_id = 0

        GObject.idle_add(self.check)

    def check(self):
        self.start_pulse()
        CinnamonDesktop.installer_check_for_packages(self.packages, self.on_check_complete)
        return False

    def on_install_clicked(self, widget):
        self.progress_bar.set_text(_("Installing"))
        self.stack.set_visible_child_name("progress")
        self.start_pulse()
        CinnamonDesktop.installer_install_packages(self.packages, self.on_install_complete)

    def pulse_progress(self):
        self.progress_bar.pulse()
        return True

    def start_pulse(self):
        self.cancel_pulse()
        self.progress_source_id = GObject.timeout_add(200, self.pulse_progress)

    def cancel_pulse(self):
        if (self.progress_source_id > 0):
            GObject.source_remove(self.progress_source_id)
            self.progress_source_id = 0

    def on_check_complete(self, result, data=None):
        self.cancel_pulse()
        if result:
            self.stack.set_visible_child_name("final")
            if self.satisfied_cb:
                self.satisfied_cb()
        else:
            self.stack.set_visible_child_name("install")

    def on_install_complete(self, result, data=None):
        self.progress_bar.set_text(self.checking_text)
        CinnamonDesktop.installer_check_for_packages(self.packages, self.on_check_complete)

class GSettingsDependencySwitch(SettingsWidget):
    def __init__(self, label, schema=None, key=None, dep_key=None, packages=None):
        super(GSettingsDependencySwitch, self).__init__(dep_key=dep_key)

        self.packages = packages

        self.content_widget = Gtk.Alignment()
        self.label = Gtk.Label(label)
        self.pack_start(self.label, False, False, 0)
        self.pack_end(self.content_widget, False, False, 0)

        self.switch = Gtk.Switch()
        self.switch.set_halign(Gtk.Align.END)
        self.switch.set_valign(Gtk.Align.CENTER)

        pkg_string = ""
        for pkg in packages:
            if pkg_string != "":
                pkg_string += ", "
            pkg_string += pkg

        self.dep_button = DependencyCheckInstallButton(_("Checking dependencies"),
                                                       _("Install: %s") % (pkg_string),
                                                       packages,
                                                       self.switch)
        self.content_widget.add(self.dep_button)

        if schema:
            self.settings = self.get_settings(schema)
            self.settings.bind(key, self.switch, "active", Gio.SettingsBindFlags.DEFAULT)

# This class is not meant to be used directly - it is only a backend for the
# settings widgets to enable them to bind attributes to gsettings keys. To use
# the gesttings backend, simply add the "GSettings" prefix to the beginning
# of the widget class name. The arguments of the backended class will be
# (label, schema, key, any additional widget-specific args and keyword args).
# (Note: this only works for classes that are gsettings compatible.)
#
# If you wish to make a new widget available to be backended, place it in the
# CAN_BACKEND list. In addition, you will need to add the following attributes
# to the widget class:
#
# bind_dir - (Gio.SettingsBindFlags) flags to define the binding direction or
#            None if you don't want the setting bound (for example if the
#            setting effects multiple attributes)
# bind_prop - (string) the attribute in the widget that will be bound to the
#             setting. This property may be omitted if bind_dir is None
# bind_object - (optional) the object to which to bind to (only needed if the
#               attribute to be bound is not a property of self.content_widget)
# map_get, map_set - (function, optional) a function to map between setting and
#                    bound attribute. May also be passed as a keyword arg during
#                    instantiation. These will be ignored if bind_dir=None
# set_rounding - (function, optional) To be used to set the digits to round to
#                if the setting is an integer
class CSGSettingsBackend(object):
    def bind_settings(self):
        if hasattr(self, "set_rounding"):
            vtype = self.settings.get_value(self.key).get_type_string()
            if vtype in ["i", "u"]:
                self.set_rounding(0)
        if hasattr(self, "bind_object"):
            bind_object = self.bind_object
        else:
            bind_object = self.content_widget
        if hasattr(self, "map_get") or hasattr(self, "map_set"):
            self.settings.bind_with_mapping(self.key, bind_object, self.bind_prop, self.bind_dir, self.map_get, self.map_set)
        elif self.bind_dir != None:
            self.settings.bind(self.key, bind_object, self.bind_prop, self.bind_dir)
        else:
            self.settings.connect("changed::"+self.key, self.on_setting_changed)
            self.on_setting_changed()

    def set_value(self, value):
        self.settings[self.key] = value

    def get_value(self):
        return self.settings[self.key]

    def get_range(self):
        range = self.settings.get_range(self.key)
        if range[0] == "range":
            return [range[1][0], range[1][1]]
        else:
            return None

def g_settings_factory(subclass):
    class NewClass(globals()[subclass], CSGSettingsBackend):
        def __init__(self, label, schema, key, *args, **kwargs):
            self.key = key
            if schema not in settings_objects.keys():
                settings_objects[schema] = Gio.Settings.new(schema)
            self.settings = settings_objects[schema]

            if kwargs.has_key("map_get"):
                self.map_get = kwargs["map_get"]
                del kwargs["map_get"]
            if kwargs.has_key("map_set"):
                self.map_set = kwargs["map_set"]
                del kwargs["map_set"]

            super(NewClass, self).__init__(label, *args, **kwargs)
            self.bind_settings()
    return NewClass

for widget in CAN_BACKEND:
    globals()["GSettings"+widget] = g_settings_factory(widget)
