import sublime_plugin, sublime, json
import re, threading, time, os

settings = {}
css = None


class IntellitipCommand(sublime_plugin.TextCommand):

    cache = {}
    menu_links = {}

    def __init__(self, view):
        self.view = view

    def run(self, edit):
        global css

        # Find db for lang
        lang = self.getLang()
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
            function_names = self.getFunctionNames(completions)
            found = False
            for function_name in function_names:
                completion = completions.get(function_name)
                if completion:
                    found = completion
                    break

            if found:
                self.view.set_status('hint', found["syntax"]+" | ")
                menus = ['<style>%s</style>' % css]
                # Syntax
                menus.append("<h1>Signature:</h1>")
                menus.append(found["syntax"])

                # Description
                menus.append("<br><br><h1>Description:</h1>")
                for descr in re.sub("(.{100,120}[\.]) ", "\\1||", found["descr"]).split("||"): #Spit long description lines
                    menus.append(descr+"<br>")

                #Parameters
                if found["params"]:
                    menus.append("<br><h1>Parameters:</h1>")

                for parameter in found["params"]:
                    menus.append(" - "+parameter["name"]+": "+parameter["descr"])
                    """for part in re.sub("(.{50,150}?)\. ", "\\1.|", parameter["descr"]).split("|"):
                        menus.append("<br>- "+part)"""

                self.view.show_popup(''.join(menus), location=-1, max_width=600)
            else:
                self.view.hide_popup()

    def getLang(self):
        scope = self.view.scope_name(self.view.sel()[0].b) #try to match against the current scope
        for match, lang in settings.get("docs").items():
            if re.match(".*"+match, scope): return lang
        self.debug(scope)
        return re.match(".*/(.*?).tmLanguage", self.view.settings().get("syntax")).group(1) #no match in predefined docs, return from syntax filename

    def getFunctionNames(self, completions):
        # Find function name
        word = self.view.word(self.view.sel()[0])
        word.a = word.a - 100 # Look back 100 character
        word.b = word.b + 1 # Ahead word +1 char
        buff = self.view.substr(word).strip()

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
        function_names.append(self.view.substr(self.view.word(self.view.sel()[0]))) #append current word
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
    global settings

    settings = sublime.load_settings("intellitip.sublime-settings")

    init_css()
