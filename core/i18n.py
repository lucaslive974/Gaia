import os

_current_lang = "en"
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
    locale_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locale")
    for lang in ["en", "pt"]:
        try:
            t = gettext.translation("messages", localedir=locale_dir, languages=[lang])
            _translations[lang] = t
        except Exception:
            po_path = os.path.join(locale_dir, lang, "messages.po")
            _translations[lang] = load_po_file(po_path)

def set_lang(lang: str):
    global _current_lang
    if lang in _translations:
        _current_lang = lang

def get_lang() -> str:
    return _current_lang

def _(key: str, **kwargs) -> str:
    lang = _current_lang
    trans_obj = _translations.get(lang)
    
    if trans_obj is not None:
        if hasattr(trans_obj, "gettext"):
            text = trans_obj.gettext(key)
        else:
            text = trans_obj.get(key)
    else:
        text = None

    if text is None or text == key:
        en_trans = _translations.get("en")
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

# Initialize translations on module load
init_i18n()
