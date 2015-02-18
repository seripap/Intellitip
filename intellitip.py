import sublime_plugin, sublime, json
import re, threading, os
from time import time

settings = {}
css = None


class IntellitipCommand(sublime_plugin.EventListener):

    cache = {}

    def on_activated(self, view):
        Pref.time = time()
        sublime.set_timeout(lambda:self.run(view, 'activated'), 0)

    def on_modified(self, view):
        Pref.time = time()

    def on_selection_modified(self, view):
        now = time()
        # if now - time > wait_time:
        sublime.set_timeout(lambda:self.run(view, 'selection_modified'), 0)
        # else:
            # sublime.set_timeout(lambda:self.display_current_class_and_function_delayed(view), int(1000*wait_time))
        Pref.time = now

    def run(self, view, where):
        global css

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
                    menus = ['<style>%s</style>' % css]
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
        # Find function name
        word = view.word(view.sel()[0])
        word.a = word.a - 100 # Look back 100 character
        word.b = word.b + 1 # Ahead word +1 char
        buff = view.substr(word).strip()

        buff = " "+re.sub(".*\n", "", buff) # Keep only last line

        # find function names ending with (
        matches = re.findall("([A-Za-z0-9_\]\.\$\)]+\.[A-Za-z0-9_\.\$]+|[A-Za-z0-9_\.\$]+[ ]*\()", buff)
        matches.reverse()
        function_names = []
        for function_name in matches:
            function_name = function_name.strip(".()[] ")
            if len(function_name) < 2: continue
            function_names.append(function_name)
            if "." in function_name:
                function_names.append(re.sub(".*\.(.*?)$", "\\1", function_name))
        function_names.append(view.substr(view.word(view.sel()[0]))) #append current word
        self.debug(function_names)
        return function_names

    def debug(self, *text):
        if settings.get("debug"):
            print(*text)

def init_css():
    global settings
    global css

    css_file = 'Packages/' + settings.get('css_file', "Intellitip/css/default.css")

    try:
        css = sublime.load_resource(css_file)
    except:
        css = None

    settings.clear_on_change('reload')
    settings.add_on_change('reload', init_css)

def plugin_loaded():
    global Pref

    class Pref:
        def load(self):
            Pref.wait_time  = 0.12
            Pref.time       = time()
            Pref.css_file   = settings.get('css_file', False)
            Pref.docs       = settings.get('docs', None)
            Pref.help_links = settings.get('help_links', None)

    settings = sublime.load_settings("intellitip.sublime-settings")
    Pref = Pref()
    Pref.load()

    settings.add_on_change('reload', lambda:Pref.load())

    init_css()
