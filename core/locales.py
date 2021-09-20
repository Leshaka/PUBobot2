import gettext
from os import listdir

locales = dict()

for locale_name in listdir("locales/compiled"):
    t = gettext.translation(
        "all", localedir="locales/compiled", languages=[locale_name]
    )
    t.install()
    locales[t.gettext("_lang")] = t.gettext

# Add default translation
t = gettext.NullTranslations()
t.install()
locales["en"] = t.gettext
