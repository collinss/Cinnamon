#!/usr/bin/python2

import sys
from ExtensionCore import ManageSpicesPage, DownloadSpicesPage
from SettingsWidgets import SidePage, SettingsStack
from Spices import Spice_Harvester
from gi.repository import GLib, Gtk

class Module:
    name = "applets"
    comment = _("Manage Cinnamon applets")
    category = "prefs"

    def __init__(self, content_box):
        self.window = None
        self.sidePage = AppletsViewSidePage(content_box, self)

    def on_module_selected(self):
        if not self.loaded:
            print "Loading Applets module"
            self.sidePage.load(self.window)

    def _setParentRef(self, window):
        self.window = window

class AppletsViewSidePage(SidePage):
    collection_type = "applet"

    def __init__(self, content_box, module):
        self.RemoveString = _("You can remove specific instances in panel edit mode via the context menu.")

        super(AppletsViewSidePage, self).__init__(_("Applets"), "cs-applets", _("applet"), content_box, module=module)

    def load(self, window):
        self.window = window

        self.spices = Spice_Harvester(self.collection_type, self.window)

        self.stack = SettingsStack()
        self.add_widget(self.stack)
        self.stack.expand = True

        manage_extensions_page = ManageAppletsPage(self, self.spices, window)
        self.stack.add_titled(manage_extensions_page, "installed", _("Manage applets"))

        download_applets_page = DownloadSpicesPage(self, self.collection_type, self.spices, window)
        self.stack.add_titled(download_applets_page, "more", _("Download applets"))

class ManageAppletsPage(ManageSpicesPage):
    directories = [("%s/.local/share/cinnamon/applets") % GLib.get_home_dir(), "/usr/share/cinnamon/applets"]
    collection_type = "applet"
    installed_page_title = _("Installed applets")
    instance_button_text = _("Add")
    remove_button_text = _("Remove")
    uninstall_button_text = _("Uninstall")
    restore_button_text = _("Default")

    def __init__(self, parent, spices, window):
        super(ManageAppletsPage, self).__init__(parent, self.collection_type, spices, window)

        if len(sys.argv) > 2 and sys.argv[1] == "applets" and sys.argv[2][0:5] == "panel":
            self.panel_id = int(sys.argv[2][5:])
        else:
            self.panel_id = int(self.settings.get_strv("panels-enabled")[0].split(":")[0])

        self.panel_select_buttons = Gtk.Box()
        self.panel_select_buttons.get_style_context().add_class("linked")
        # self.previous_button = Gtk.Button.new_from_icon_name('go-previous-symbolic', Gtk.IconSize.BUTTON)
        self.previous_button = Gtk.Button(label=_("Previous Panel"))
        self.previous_button.set_no_show_all(False)
        self.previous_button.connect("clicked", self.previous_panel)
        self.panel_select_buttons.add(self.previous_button)
        # self.next_button = Gtk.Button.new_from_icon_name('go-next-symbolic', Gtk.IconSize.BUTTON)
        self.next_button = Gtk.Button(label=_("Next Panel"))
        self.next_button.set_no_show_all(False)
        self.next_button.connect("clicked", self.next_panel)
        self.panel_select_buttons.add(self.next_button)
        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)
        size_group.add_widget(self.previous_button)
        size_group.add_widget(self.next_button)

        self.spices.send_proxy_signal('highlightPanel', '(ib)', self.panel_id, True)

        self.connect("map", self.restore_highlight)
        self.connect("unmap", self.remove_highlight)
        self.connect("destroy", self.remove_highlight)
        self.settings.connect('changed:: panels-enabled', self.panels_changed)
        self.panels_changed()

        self.top_box.pack_start(self.panel_select_buttons, False, False, 0)

    def previous_panel(self, *args):
        self.spices.send_proxy_signal('highlightPanel', '(ib)', self.panel_id, False)

        panels = self.settings.get_strv("panels-enabled")
        for i in range(len(panels)):
            if int(panels[i].split(":")[0]) == self.panel_id:
                index = i
                break

        if index - 1 >= 0:
            self.panel_id = int(panels[index - 1].split(":")[0])
        else:
            self.panel_id = int(panels[len(panels) - 1].split(":")[0])

        self.spices.send_proxy_signal('highlightPanel', '(ib)', self.panel_id, True)

    def next_panel(self, widget):
        self.spices.send_proxy_signal('highlightPanel', '(ib)', self.panel_id, False)

        panels = self.settings.get_strv("panels-enabled")
        for i in range(len(panels)):
            if int(panels[i].split(":")[0]) == self.panel_id:
                index = i
                break

        if index + 1 < len(panels):
            self.panel_id = int(panels[index + 1].split(":")[0])
        else:
            self.panel_id = int(panels[0].split(":")[0])

        self.spices.send_proxy_signal('highlightPanel', '(ib)', self.panel_id, True)

    def panels_changed(self, *args):
        if len(self.settings.get_strv('panels-enabled')) > 1:
            self.previous_button.show()
            self.next_button.show()
        else:
            self.previous_button.hide()
            self.next_button.hide()

    def remove_highlight(self, *args):
        self.spices.send_proxy_signal('highlightPanel', '(ib)', self.panel_id, False)

    def restore_highlight(self, *args):
        self.spices.send_proxy_signal('highlightPanel', '(ib)', self.panel_id, True)

    def enable(self, uuid):
        applet_id = self.settings.get_int("next-applet-id");
        self.settings.set_int("next-applet-id", (applet_id+1));

        # we want to position the applet on right side of the left section
        new_list = []
        position = 0
        for applet_string in self.enabled_extensions:
            info = applet_string.split(':')
            # we need to shift any applets in the same section
            if info[0] == 'panel%d' % self.panel_id and info[1] == 'right':
                info[2] = str(int(info[2]) + 1)
                applet_string = ':'.join(info)
            new_list.append(applet_string)

        info_string = 'panel%d:right:0:%s:%d' % (self.panel_id, uuid, applet_id)
        new_list.append(info_string)
        self.enabled_extensions = new_list

        self.settings.set_strv(("enabled-%ss") % (self.collection_type), self.enabled_extensions)

