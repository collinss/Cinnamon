#!/usr/bin/env python2

from SettingsWidgets import *
import gi
gi.require_version('Notify', '0.7')
from gi.repository import GObject, Notify

content = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit. \
Suspendisse eleifend, lacus ut tempor vehicula, lorem tortor \
suscipit libero, sit amet congue odio libero vitae lacus. \
Sed est nibh, lacinia ac magna non, blandit aliquet est. \
Mauris volutpat est vel lacinia faucibus. Pellentesque \
pulvinar eros at dolor pretium, eget hendrerit leo rhoncus. \
Sed nisl leo, posuere eget risus vel, euismod egestas metus. \
Praesent interdum, dui sit amet convallis rutrum, velit nunc \
sollicitudin erat, ac viverra leo eros in nulla. Morbi feugiat \
feugiat est. Nam non libero dolor. Duis egestas sodales massa \
sit amet lobortis. Donec sit amet nisi turpis. Morbi aliquet \
aliquam ullamcorper.
"""

MEDIA_KEYS_OSD_SIZES = [
    ("disabled", _("Disabled")),
    ("small", _("Small")),
    ("medium", _("Medium")),
    ("large", _("Large"))
]

class Module:
    name = "notifications"
    comment = _("Notification preferences")
    category = "prefs"

    def __init__(self, content_box):
        keywords = _("notifications")
        sidePage = SidePage(_("Notifications"), "cs-notifications", keywords, content_box, module=self)
        self.sidePage = sidePage

    def on_module_selected(self):
        if self.loaded:
            return

        print "Loading Notifications module"

        Notify.init("cinnamon-settings-notifications-test")

        page = SettingsPage()
        self.sidePage.add_widget(page)

        settings = page.add_section(_("Notification settings"))

        switch = g_settings_factory(Switch, _("Enable notifications"), "org.cinnamon.desktop.notifications", "display-notifications")
        settings.add_row(switch)

        switch = g_settings_factory(Switch, _("Remove notifications after their timeout is reached"), "org.cinnamon.desktop.notifications", "remove-old")
        settings.add_reveal_row(switch, "org.cinnamon.desktop.notifications", "display-notifications")

        switch = g_settings_factory(Switch, _("Have notifications fade out when hovered over"), "org.cinnamon.desktop.notifications", "fade-on-mouseover")
        settings.add_reveal_row(switch, "org.cinnamon.desktop.notifications", "display-notifications")

        spin = g_settings_factory(SpinButton, _("Hover opacity"), "org.cinnamon.desktop.notifications", "fade-opacity", _("%"), 0, 100)
        settings.add_reveal_row(spin)
        spin.revealer.settings = Gio.Settings.new("org.cinnamon.desktop.notifications")

        def on_settings_changed(*args):
            spin.revealer.set_reveal_child(spin.revealer.settings["fade-on-mouseover"] and spin.revealer.settings["display-notifications"])
        spin.revealer.settings.connect("changed::fade-on-mouseover", on_settings_changed)
        spin.revealer.settings.connect("changed::display-notifications", on_settings_changed)
        on_settings_changed()

        widget = SettingsWidget()
        button = Gtk.Button(label = _("Display a test notification"))
        button.connect("clicked", self.send_test)
        widget.pack_start(button, True, True, 0)
        settings.add_row(widget)

        settings = page.add_section(_("Media keys OSD"))

        combo = g_settings_factory(ComboBox, _("Media keys OSD size"), "org.cinnamon", "show-media-keys-osd", MEDIA_KEYS_OSD_SIZES)
        settings.add_row(combo)

    def send_test(self, widget):
        n = Notify.Notification.new("This is a test notification", content, "dialog-warning")
        n.show()
