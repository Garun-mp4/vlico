"""Two outreach audiences; ambiguous source categories require operator review."""

DESIGNERS = "Дизайнеры и архитекторы"
BUILDERS = "Строители и бригады"
REVIEW = "Требует уточнения"


def classify(category, *, designer_directory=False):
    if designer_directory:
        return DESIGNERS
    text = str(category or "").casefold().strip()
    if not text or any(word in text for word in ("уточнить", "проверить", "смежные")):
        return REVIEW
    design = any(word in text for word in ("дизайн", "архитект"))
    build = any(word in text for word in (
        "строит", "ремонт", "отделк", "отделоч", "прораб", "бригад", "монтаж", "электри", "застройщик",
    ))
    if design and build:
        return REVIEW
    if design:
        return DESIGNERS
    if build or text == "инженерные коммуникации":
        return BUILDERS
    return REVIEW


def segment_group(value):
    segment = classify(value)
    return {DESIGNERS: "designer", BUILDERS: "builder"}.get(segment)
