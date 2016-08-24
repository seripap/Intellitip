"""
IntelliTip plugin for Sublime Text 3.
"""

import json
import os
import re
import webbrowser

import sublime
import sublime_plugin


def load_css_file_to_settings(settings):
    css_file = "Packages/" + settings.get("css_file", "Intellitip/css/default.css")

    css = sublime.load_resource(css_file).replace("\r", "")

    settings.set("css", css)


def get_function_names(view):
    return [view.substr(view.word(view.sel()[0]))]


class IntellitipCommand(sublime_plugin.TextCommand):
    cache    = {}
    lang     = None
    settings = None

    def __init__(self, view):
        super(IntellitipCommand, self).__init__(view)

        self.load_settings()

    def load_settings(self):
        self.settings = sublime.load_settings("intellitip.sublime-settings")

        load_css_file_to_settings(self.settings)

    def run(self, _):
        view_settings = self.view.settings()

        if view_settings.get('is_widget'):
            return

        for region in self.view.sel():
            region_row, _ = self.view.rowcol(region.begin())

            if region_row != view_settings.get('intellitip_row', -1):
                view_settings.set('intellitip_row', region_row)
            else:
                return

            # Find db for lang
            self.get_lang(self.view)
            print(self.lang)

            if self.lang not in self.cache:
                path_db = os.path.dirname(os.path.abspath(__file__)) + "/db/%s.json" % self.lang

                if os.path.exists(path_db):
                    self.cache[self.lang] = json.load(open(path_db))
                else:
                    self.cache[self.lang] = {}

            completions = self.cache[self.lang]

            # Find in completions
            if completions:
                function_names = get_function_names(self.view)
                found = False

                for function_name in function_names:
                    completion = completions.get(function_name)

                    if completion:
                        found = completion
                        break

                if found:
                    menus = ['<style>%s</style>' % self.settings.get("css")]

                    # Syntax
                    menus.append("<h1>%s</h1>" % found["syntax"])

                    # Spit long description lines
                    for descr in re.sub("(.{100,120}[\\.]) ", "\\1||", found["descr"]).split("||"):
                        menus.append("<br>" + descr + "<br>")

                    # Parameters
                    if found["params"]:
                        menus.append("<h1>Parameters:</h1>")

                    for parameter in found["params"]:
                        menus.append("- <b>" + parameter["name"] + ":</b> " + parameter["descr"] + "<br>")

                    self.append_links(menus, found)

                    self.view.show_popup(''.join(menus), location = -1, max_width = 600, on_navigate = self.on_navigate)
                else:
                    self.view.hide_popup()

    def append_links(self, menus, found):
        for pattern, _ in sorted(self.settings.get("help_links").items()):
            if re.match(pattern, found["path"]):
                menus.append('<br>Open docs: <a href="%s">Docs</a>' % found["name"])
                break

        return menus

    def get_lang(self, view):
        # Try to match against the current scope
        scope = view.scope_name(view.sel()[0].b)

        for match, lang in self.settings.get("docs").items():
            if re.match(".*" + match, scope):
                self.lang = lang
                return

        syntax = view.settings().get("syntax")

        # No match in predefined docs, return from syntax filename
        matched = re.match(".*/(.*?).sublime-syntax", syntax)

        if matched:
            self.lang = matched.group(1)
            return

        # No match in syntax filename, try tmLanguage
        matched = re.match(".*/(.*?).tmLanguage", syntax)

        if matched:
            self.lang = matched.group(1)
            return

        self.lang = None

    def on_navigate(self, link):
        webbrowser.open_new_tab(self.settings.get("help_links")[self.lang.lower()] % link)
