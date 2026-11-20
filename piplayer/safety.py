"""Keeps explicit content out of the browse shelves (topic shelves, trending, suggestions).

Each source tells us differently: YouTube Music marks explicit songs (`isExplicit`), YouTube marks age-restricted
videos (`age_limit` 18+), SoundCloud says nothing. So an item is also dropped when its title or artist contains an
explicit marker or strong profanity. Searches the user types themselves are not filtered.
"""
import re

_WORDS = (r"explicit|uncensored|unrated|nsfw|18\+|21\+|adults? only|parental advisory|dirty|xxx|porn\w*|nude|naked|hentai|onlyfans|"
          r"strip ?club|sex|sexual|sexy|horny|twerk\w*|booty|orgy|erotic\w*|orgasm|blowjob|"
          r"f+[u*@#]+c+k\w*|f[*@#]+k\w*|sh[i1*@#]+t\w*|b[i1*@#]+tch\w*|c[u*]+nt\w*|d[i1*]+ck(?:s|y|head|heads)?|pussy|pussies|"
          r"n[i1*]+gg\w*|wh[o0*]+re\w*|sl[u*]+t\w*|ass(?:hole)?s?|a\$\$\w*|motherf\w*|mf'?er\w*|bs?tards?|"
          r"weed|cocaine|molly|get high|high af|drugs?|gangsta|thug")
_BAD = re.compile(rf"(?<![a-z0-9])(?:{_WORDS})(?![a-z0-9])", re.I)
_TAG = re.compile(r"[\(\[]\s*e\s*[\)\]]", re.I)             # a bare "(E)" tag some uploaders use


def is_clean(item):
    """False for an item flagged explicit by its source or whose title / artist looks explicit."""
    if item.get("explicit"):
        return False
    text = f"{item.get('title') or ''} {item.get('artist') or ''}"
    return not (_BAD.search(text) or _TAG.search(text))


def only_clean(items):
    return [i for i in items or [] if is_clean(i)]
