"""
IntelliTip plugin for Sublime Text 3.
"""

import json
import os
import re
import webbrowser

import sublime
import sublime_plugin


class IntellitipCommand(sublime_plugin.TextCommand):
    """
    The only class for this plugin.
    """

    cached_completions = {}
    settings           = None

    def __init__(self, view):
        super(IntellitipCommand, self).__init__(view)

        self.load_settings()

    def load_settings(self):
        """
        Loads settings from configuration file and loads necessary resources.
        """

        self.settings = sublime.load_settings("intellitip.sublime-settings")
        self.load_css_file_to_settings()

    def load_css_file_to_settings(self):
        """
        Reads CSS content from file specified in settings
        and add its content to the settings, so it's available anytime later.
        """

        css_file = "Packages/" + self.settings.get("css_file", "Intellitip/css/default.css")

        css = sublime.load_resource(css_file).replace("\r", "")

        self.settings.set("css", css)

    def get_selected_function_name(self):
        """
        Extracts function name (current word) from selection.
        """

        selection = self.view.sel()[0]
        word      = self.view.word(selection)

        return self.view.substr(word)

    def get_language(self):
        """
        Reads language being used from configuration, sublime syntax settings,
        or TM language settings (whichever is defined first).

        Returns None on failure.
        """

        language = None

        # Try to match against the current scope
        scope = self.view.scope_name(self.view.sel()[0].b)

        for config_pattern, config_language in self.settings.get("docs").items():
            if re.match(".*" + config_pattern, scope):
                return config_language

        syntax = self.view.settings().get("syntax")

        # No match in predefined docs, return from syntax filename
        matched = re.match(".*/(.*?).sublime-syntax", syntax)

        if matched:
            return matched.group(1)

        # No match in syntax filename, try tmLanguage
        matched = re.match(".*/(.*?).tmLanguage", syntax)

        if matched:
            return matched.group(1)

        return language

    def add_completions_to_cache(self, language):
        """
        Adds completions for specified language from file to cache.
        If completions are not available, adds empty dict instead.
        """

        path_db = os.path.dirname(os.path.abspath(__file__)) + "/db/%s.json" % language

        if os.path.exists(path_db):
            completions = json.load(open(path_db))
        else:
            completions = {}

        self.cached_completions[language] = completions

    def get_completions_from_cache(self, language):
        """
        Returns cached completions for specified language.
        If completions are not in cache, they're added to it first.
        In case there are no completions defined for the language,
        empty dict is returned instead.
        """

        if language not in self.cached_completions:
            self.add_completions_to_cache(language)

        return self.cached_completions[language]

    def build_completion_html(self, completion_data):
        """
        Creates HTML containing completions.
        """

        html_message = []

        html_message.append("<style>%s</style>" % self.settings.get("css"))
        html_message.append("<h1>%s</h1>"       % completion_data["syntax"])
        html_message.append("<br>%s<br>"        % completion_data["descr"])

        if completion_data["params"]:
            html_message.append("<h1>Parameters:</h1>")

        for parameter in completion_data["params"]:
            html_message.append("- <b>" + parameter["name"] + ":</b> " + parameter["descr"] + "<br>")

        for pattern, _ in sorted(self.settings.get("help_links").items()):
            if re.match(pattern, completion_data["path"]):
                html_message.append('<br>Open docs: <a href="%s">Docs</a>' % completion_data["name"])
                break

        return ''.join(html_message)

    def on_navigate(self, link, language):
        """
        On-click handler for links in completion popup.
        Opens a browser with specified link.
        """

        webbrowser.open_new_tab(self.settings.get("help_links")[language.lower()] % link)

    def run(self, _):
        """
        Executes the plugin.
        Reads language settings, completions for it and displays a popup containg it.
        """

        language = self.get_language()
        completions_for_language = self.get_completions_from_cache(language)

        if not completions_for_language:
            sublime.status_message("Could not find any completions for %s" % language)
            return

        selected_function_name  = self.get_selected_function_name()
        completion_for_function = completions_for_language.get(selected_function_name)

        if not completion_for_function:
            sublime.status_message("Could not find any completions for %s :: %s" % (language, selected_function_name))
            return

        help_message = self.build_completion_html(completion_for_function)

        self.view.show_popup(help_message,
                             max_width   = 1200,
                             max_height  = 1200,
                             on_navigate = lambda link: self.on_navigate(link, language))
