import os
from enum import Enum

class Language(Enum):
    PT_BR = "pt_BR"
    EN_US = "en_US"


def get_system_lang() -> Language:
    import locale
    import os
    try:
        sys_lang, _ = locale.getlocale()
        if sys_lang:
            sys_lang = sys_lang.lower()
            if sys_lang.startswith("pt"):
                return Language.PT_BR
            if sys_lang.startswith("en"):
                return Language.EN_US
    except Exception:
        pass

    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var)
        if val:
            val = val.lower()
            if val.startswith("pt"):
                return Language.PT_BR
            if val.startswith("en"):
                return Language.EN_US
    return Language.EN_US


_current_lang = get_system_lang()
_translations = {}


def load_po_file(filepath: str) -> dict[str, str]:
    trans = {}
    if not os.path.exists(filepath):
        return trans
        
    with open(filepath, "r", encoding="utf-8") as f:
        msgid = None
        msgstr = None
        in_msgid = False
        in_msgstr = False
        
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            
            if line.startswith("msgid"):
                if msgid is not None and msgstr is not None:
                    trans[msgid] = msgstr
                    msgid = None
                    msgstr = None
                in_msgid = True
                in_msgstr = False
                msgid = line[5:].strip().strip('"')
            elif line.startswith("msgstr"):
                in_msgid = False
                in_msgstr = True
                msgstr = line[6:].strip().strip('"')
            elif line.startswith('"') and line.endswith('"'):
                val = line[1:-1]
                if in_msgid:
                    msgid += val
                elif in_msgstr:
                    msgstr += val
                
        # Handle last key/value in file
        if msgid is not None and msgstr is not None:
            trans[msgid] = msgstr
    return trans


def init_i18n():
    global _translations
    import gettext
    locale_dir = os.path.join(os.path.dirname(__file__), "locale")
    
    dir_mapping = {
        Language.PT_BR: "pt",
        Language.EN_US: "en",
    }
    
    for lang_enum, dir_name in dir_mapping.items():
        try:
            t = gettext.translation("messages", localedir=locale_dir, languages=[dir_name])
            _translations[lang_enum] = t
        except Exception:
            po_path = os.path.join(locale_dir, dir_name, "messages.po")
            _translations[lang_enum] = load_po_file(po_path)


def set_lang(lang: Language | str):
    global _current_lang
    if isinstance(lang, str):
        if lang == "pt":
            lang = Language.PT_BR
        elif lang == "en":
            lang = Language.EN_US
        else:
            return

    if lang in Language:
        _current_lang = lang


def get_lang() -> Language:
    return _current_lang


def _(key: str, **kwargs) -> str:
    lang_enum = _current_lang
    trans_obj = _translations.get(lang_enum)
    
    if trans_obj is not None:
        if hasattr(trans_obj, "gettext"):
            text = trans_obj.gettext(key)
        else:
            text = trans_obj.get(key)
    else:
        text = None

    if text is None or text == key:
        en_trans = _translations.get(Language.EN_US)
        if en_trans is not None:
            if hasattr(en_trans, "gettext"):
                text = en_trans.gettext(key)
            else:
                text = en_trans.get(key)
        else:
            text = None

    if text is None:
        text = key

    if kwargs:
        return text.format(**kwargs)
    return text


def parse_lang_from_argv(argv: list[str]) -> str:
    lang = "en"
    sys_lang = get_system_lang()
    if sys_lang == Language.PT_BR:
        lang = "pt"

    for idx, arg in enumerate(argv):
        if arg in ("--lang", "-l"):
            if idx + 1 < len(argv):
                candidate = argv[idx + 1]
                if candidate in ("en", "pt"):
                    lang = candidate
            break
    return lang


# Initialize translations on module load
init_i18n()
