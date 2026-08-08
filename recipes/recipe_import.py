"""Best-effort recipe extraction from a web page's schema.org/Recipe JSON-LD block.

Most recipe sites publish structured data for search engines, so reading that is far more reliable
than scraping arbitrary HTML -- and needs no LLM. Sites without it aren't handled: the caller falls
back to telling the user to enter the recipe manually, rather than guessing from prose.

Everything here is deliberately tolerant: any field that can't be read cleanly comes back empty
instead of raising, because the result is shown to the user for review before anything is saved.
"""

import json
import re
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation

FETCH_TIMEOUT_SECONDS = 8
# Recipe pages are HTML; anything much larger than this is not a page we can use, and reading it
# in full would tie up the worker for no reason.
MAX_FETCH_BYTES = 3 * 1024 * 1024
# Some sites 403 the default Python user agent.
USER_AGENT = "Mozilla/5.0 (compatible; ForkCast/0.1; +https://github.com/MatthieuPerrodin/ForkCast)"

JSON_LD_RE = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
HTML_TAG_RE = re.compile(r"<[^>]+>")
# ISO 8601 durations as used by schema.org prepTime/cookTime, e.g. "PT1H30M".
ISO_DURATION_RE = re.compile(r"^P(?:\d+D)?T(?:(\d+)H)?(?:(\d+)M)?", re.IGNORECASE)
# "400 g de spaghetti" / "2 cups flour" / "3 oeufs" -> quantity, optional unit, name.
INGREDIENT_LINE_RE = re.compile(
    r"^\s*(\d+(?:[.,]\d+)?)\s*([^\W\d_]+)?\s*(?:de\s+|d'|of\s+)?(.*)$",
    re.UNICODE,
)
# Words that look like a unit in the position after the number. Anything else there is treated as
# part of the ingredient name instead (e.g. "3 oeufs" -> 3, no unit, "oeufs").
KNOWN_UNITS = {
    "g", "kg", "mg", "ml", "cl", "dl", "l", "oz", "lb", "lbs",
    "c", "tsp", "tbsp", "cup", "cups", "tasse", "tasses",
    "cuillere", "cuillère", "cuilleres", "cuillères",
    "pincee", "pincée", "gousse", "gousses", "tranche", "tranches",
    "sachet", "sachets", "boite", "boîte", "pot", "pots",
}


class RecipeImportError(Exception):
    """Raised when the page can't be fetched or holds no usable Recipe data."""


def _fetch_html(url):
    if not url.lower().startswith(("http://", "https://")):
        raise RecipeImportError("L'adresse doit commencer par http:// ou https://.")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_FETCH_BYTES)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise RecipeImportError("La page n'a pas pu être chargée.") from exc
    return raw.decode("utf-8", errors="replace")


def _iter_json_ld_objects(html):
    """Yields every JSON-LD object on the page, flattening arrays and @graph wrappers, which
    different site generators use interchangeably for the same content."""
    for block in JSON_LD_RE.findall(html):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        pending = data if isinstance(data, list) else [data]
        while pending:
            node = pending.pop()
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                pending.extend(graph)
            yield node


def _is_recipe(node):
    node_type = node.get("@type", "")
    types = node_type if isinstance(node_type, list) else [node_type]
    return any(str(t).lower() == "recipe" for t in types)


def _clean_text(value):
    if not isinstance(value, str):
        return ""
    return " ".join(HTML_TAG_RE.sub(" ", value).split())


def _first_text(value):
    """schema.org fields are routinely a string, a list, or a nested object -- normalise to text."""
    if isinstance(value, list):
        return _first_text(value[0]) if value else ""
    if isinstance(value, dict):
        return _clean_text(value.get("text") or value.get("name") or "")
    return _clean_text(value)


def parse_iso_duration_minutes(value):
    if not isinstance(value, str):
        return None
    match = ISO_DURATION_RE.match(value.strip())
    if not match or not any(match.groups()):
        return None
    hours, minutes = match.groups()
    return int(hours or 0) * 60 + int(minutes or 0)


def parse_servings(value):
    # recipeYield is legitimately a bare number as often as it is text ("4 portions"), so numbers
    # have to be handled before _first_text, which only speaks strings/lists/dicts.
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"\d+", _first_text(value))
    return int(match.group()) if match else None


def parse_ingredient_line(line):
    """Splits "400 g de spaghetti" into (Decimal("400"), "g", "spaghetti"). Falls back to
    (None, "", <whole line>) whenever the shape isn't recognisable -- a wrong quantity is worse
    than no quantity, and the user reviews the result before saving either way.
    """
    text = _clean_text(line)
    if not text:
        return None, "", ""
    match = INGREDIENT_LINE_RE.match(text)
    if not match:
        return None, "", text
    raw_quantity, maybe_unit, rest = match.groups()
    try:
        quantity = Decimal(raw_quantity.replace(",", "."))
    except InvalidOperation:
        return None, "", text

    unit = ""
    name = rest.strip()
    if maybe_unit:
        if maybe_unit.lower() in KNOWN_UNITS:
            unit = maybe_unit.lower()
        else:
            # Not a unit after all -- it was the start of the name ("3 oeufs frais").
            name = f"{maybe_unit} {name}".strip()
    return quantity, unit, name or text


def _parse_instructions(value):
    """recipeInstructions is either a list of strings, a list of HowToStep objects, a HowToSection
    with nested steps, or one blob of text with newlines."""
    steps = []
    if isinstance(value, str):
        steps = [s for s in (_clean_text(p) for p in value.splitlines()) if s]
    elif isinstance(value, list):
        for entry in value:
            if isinstance(entry, dict) and isinstance(entry.get("itemListElement"), list):
                steps.extend(_parse_instructions(entry["itemListElement"]))
            else:
                text = _first_text(entry)
                if text:
                    steps.append(text)
    elif isinstance(value, dict):
        steps = _parse_instructions(value.get("itemListElement") or value.get("text") or "")
    return steps


def import_recipe_from_url(url):
    """Returns a dict of draft recipe fields for the user to review. Raises RecipeImportError if
    the page can't be read or carries no schema.org Recipe."""
    html = _fetch_html(url)
    recipe_node = next((n for n in _iter_json_ld_objects(html) if _is_recipe(n)), None)
    if recipe_node is None:
        raise RecipeImportError(
            "Aucune recette structurée (schema.org) trouvée sur cette page. "
            "Il faut la saisir à la main."
        )

    title = _first_text(recipe_node.get("name"))
    if not title:
        raise RecipeImportError("La recette trouvée n'a pas de titre exploitable.")

    raw_ingredients = recipe_node.get("recipeIngredient") or recipe_node.get("ingredients") or []
    if isinstance(raw_ingredients, str):
        raw_ingredients = [raw_ingredients]

    return {
        "title": title[:150],
        "description": _first_text(recipe_node.get("description"))[:2000],
        "prep_time_min": parse_iso_duration_minutes(recipe_node.get("prepTime")),
        "cook_time_min": parse_iso_duration_minutes(recipe_node.get("cookTime")),
        "default_servings": parse_servings(recipe_node.get("recipeYield")),
        "ingredients": [
            parse_ingredient_line(line) for line in raw_ingredients if _clean_text(line)
        ],
        "steps": _parse_instructions(recipe_node.get("recipeInstructions")),
        "source_url": url,
    }
