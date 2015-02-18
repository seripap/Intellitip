import sublime_plugin, sublime, json
import re, os
from time import time


class IntellitipCommand(sublime_plugin.EventListener):

    cache = {}
    region_row = []

    def on_activated(self, view):
        Pref.time = time()
        sublime.set_timeout(lambda:self.run(view, 'activated'), 0)

    def on_modified(self, view):
        Pref.time = time()

    def on_selection_modified(self, view):
        now = time()
        sublime.set_timeout(lambda:self.run(view, 'selection_modified'), 0)
        Pref.time = now

    def run(self, view, where):
        global region_row

        view_settings = view.settings()
        if view_settings.get('is_widget'):
            return

        for region in view.sel():
            region_row, region_col = view.rowcol(region.begin())

            if region_row != view_settings.get('intellitip_row', -1):
                view_settings.set('intellip_row', region_row)
            else:
                return

            # Find db for lang
            lang = self.getLang(view)
            if lang not in self.cache: #DEBUG disable cache: or 1 == 1
                path_db = os.path.dirname(os.path.abspath(__file__))+"/db/%s.json" % lang
                self.debug("Loaded intelliDocs db:", path_db)

                if os.path.exists(path_db):
                    self.cache[lang] = json.load(open(path_db))
                else:
                    self.cache[lang] = {}

            completions = self.cache[lang]

            # Find in completions
            if completions:
                function_names = self.getFunctionNames(view, completions)
                found = False
                for function_name in function_names:
                    completion = completions.get(function_name)
                    if completion:
                        found = completion
                        break

                if found:
                    menus = ['<style>%s</style>' % Pref.css]
                    # Syntax
                    menus.append("<h1>Signature:</h1>")
                    menus.append(found["syntax"])

                    for descr in re.sub("(.{100,120}[\.]) ", "\\1||", found["descr"]).split("||"): #Spit long description lines
                        menus.append("<br>"+descr+"<br>")

                    #Parameters
                    if found["params"]:
                        menus.append("<br><h1>Parameters:</h1>")

                    for parameter in found["params"]:
                        menus.append("- <b>"+parameter["name"]+":</b> "+parameter["descr"]+"<br>")

                    view.show_popup(''.join(menus), location=-1, max_width=600)
                else:
                    view.hide_popup()

    def getLang(self, view):
        scope = view.scope_name(view.sel()[0].b) #try to match against the current scope
        for match, lang in Pref.docs.items():
            if re.match(".*"+match, scope): return lang
        self.debug(scope)
        return re.match(".*/(.*?).tmLanguage", view.settings().get("syntax")).group(1) #no match in predefined docs, return from syntax filename

    def getFunctionNames(self, view, completions):
        global region_row
        return [view.substr(view.word(view.sel()[0]))]

    def debug(self, *text):
        if Pref.debug:
            print(*text)

def init_css():
    css_file = 'Packages/' + Pref.css_file

    try:
        Pref.css = sublime.load_resource(css_file)
    except:
        Pref.css = None

def plugin_loaded():
    global Pref

    class Pref:
        def load(self):
            Pref.wait_time = 0.12
            Pref.time      = time()
            Pref.css_file  = settings.get('css_file', "Intellitip/css/default.css")
            Pref.docs      = settings.get('docs', None)
            Pref.debug     = settings.get('debug', False)
            Pref.css       = None

    settings = sublime.load_settings("intellitip.sublime-settings")
    Pref = Pref()
    Pref.load()
    init_css()

    settings.add_on_change('reload', lambda:Pref.load())
