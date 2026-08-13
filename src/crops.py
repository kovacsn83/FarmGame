# A `growth_time` kulcs külső kiegészítések kompatibilitási aliasa; az új
# játékkód a `growth_weeks` értéket használja.
CROPS = {
    "wheat": {
        "name": "Búza",
        "growth_weeks": 38,
        "growth_time": 38,
        "planting_weeks": ((40, 43),),
        "harvest_weeks": ((26, 33),),
        "yield": 8,
        "price": 10.00,
        "seed_cost": 5.00,
        "colors": ((120, 220, 120), (50, 170, 50), (30, 120, 30),
                   (180, 190, 60), (220, 190, 60)),
    },
    "corn": {
        "name": "Kukorica",
        "growth_weeks": 21,
        "growth_time": 21,
        "planting_weeks": ((15, 18),),
        "harvest_weeks": ((36, 43),),
        "yield": 9,
        "price": 12.00,
        "seed_cost": 6.00,
        "colors": ((110, 190, 90), (55, 145, 55), (85, 135, 35),
                   (155, 170, 35), (205, 185, 45)),
    },
    "tomato": {
        "name": "Paradicsom",
        "growth_weeks": 9,
        "growth_time": 9,
        "planting_weeks": ((19, 22),),
        "harvest_weeks": ((28, 39),),
        "harvest_stages": (
            {"growth_weeks": 9, "yield": 4},
            {"growth_weeks": 3, "yield": 2},
        ),
        # A második szedés csak sikeres első aratás után, ugyanabban
        # az évi normál vagy pótaratási ablakban indulhat el.
        "next_stage_requires_same_harvest_season": True,
        "yield": 6,
        "price": 16.00,
        "seed_cost": 8.00,
        "colors": ((110, 210, 110), (45, 160, 55), (30, 125, 45),
                   (190, 85, 45), (220, 45, 40)),
    },
    "alfalfa": {
        "name": "Lucerna",
        "growth_weeks": 10,
        "growth_time": 10,
        "planting_weeks": ((11, 14),),
        "harvest_weeks": ((15, 40),),
        "recurring_harvest": {
            "first_growth_weeks": 10,
            "regrowth_weeks": 5,
            "yield": 3,
            "lifespan_weeks": 135,
            "reset_fertilized_after_harvest": True,
        },
        "yield": 3,
        "price": 7.00,
        "seed_cost": 4.00,
        "colors": ((150, 225, 135), (95, 195, 90), (55, 165, 70),
                   (35, 135, 55), (25, 105, 45)),
    },
}

# A rendes aratási időszakot követő, minden növényre egységes pótidő.
LATE_HARVEST_DURATION_WEEKS = 2
LATE_HARVEST_YIELD_MULTIPLIER = 0.5


def get_crop_definition(crop):
    return CROPS.get(crop) if isinstance(crop, str) else crop


def get_crop_growth_weeks(crop):
    """Az új érési adatot, régi definíciónál a kompatibilis kulcsot adja."""
    definition = get_crop_definition(crop)
    if definition is None:
        return None
    return definition.get("growth_weeks", definition.get("growth_time"))


def get_crop_harvest_stages(crop):
    """Az aratási szakaszokat egységesen adja vissza egyszeri növénynél is."""
    definition = get_crop_definition(crop)
    if definition is None:
        return ()
    stages = definition.get("harvest_stages")
    if stages is not None:
        return tuple(stages)
    recurring = definition.get("recurring_harvest")
    if recurring is not None:
        return (
            {
                "growth_weeks": recurring["first_growth_weeks"],
                "yield": recurring["yield"],
            },
            {
                "growth_weeks": recurring["regrowth_weeks"],
                "yield": recurring["yield"],
            },
        )
    return ({
        "growth_weeks": get_crop_growth_weeks(definition),
        "yield": definition["yield"],
    },)


def get_current_harvest_stage(crop, harvest_count=0):
    """A következő, még el nem végzett aratási szakaszt adja vissza."""
    stages = get_crop_harvest_stages(crop)
    if not isinstance(harvest_count, int) or isinstance(harvest_count, bool):
        harvest_count = 0
    definition = get_crop_definition(crop)
    recurring = definition.get("recurring_harvest") if definition else None
    if recurring is not None and harvest_count >= 1:
        return stages[1]
    if not 0 <= harvest_count < len(stages):
        return None
    return stages[harvest_count]


def get_current_growth_weeks(crop, harvest_count=0):
    """Az aktuális aratási szakasz érési idejét adja vissza."""
    stage = get_current_harvest_stage(crop, harvest_count)
    return stage.get("growth_weeks") if stage is not None else None


def get_current_base_yield(crop, harvest_count=0):
    """Az aktuális aratási szakasz adatvezérelt alaphozamát adja vissza."""
    stage = get_current_harvest_stage(crop, harvest_count)
    return stage.get("yield") if stage is not None else None


def get_crop_lifespan_weeks(crop):
    """Az abszolút hétindexen mért hasznos élettartamot adja vissza."""
    definition = get_crop_definition(crop)
    recurring = definition.get("recurring_harvest") if definition else None
    return recurring.get("lifespan_weeks") if recurring is not None else None


def crop_has_recurring_harvest(crop):
    definition = get_crop_definition(crop)
    return bool(definition and definition.get("recurring_harvest"))


def crop_resets_fertilizer_after_harvest(crop):
    definition = get_crop_definition(crop)
    recurring = definition.get("recurring_harvest") if definition else None
    return bool(
        recurring and recurring.get("reset_fertilized_after_harvest", False)
    )


def crop_has_more_harvests(crop, completed_harvests):
    """Véges és ismétlődő ciklusnál is jelzi a következő aratást."""
    if crop_has_recurring_harvest(crop):
        return True
    return completed_harvests < len(get_crop_harvest_stages(crop))


def get_crop_week_intervals(crop, interval_name):
    """Több, akár évhatáron átnyúló időablak közös lekérdezése."""
    definition = get_crop_definition(crop)
    if definition is None:
        return None
    intervals = definition.get(interval_name)
    return None if intervals is None else tuple(intervals)


def is_week_in_intervals(week, intervals):
    """Hiányzó intervallumnál korlátozás nélkül, egyébként adatvezérelten dönt."""
    if intervals is None:
        return True
    for start_week, end_week in intervals:
        if start_week <= end_week:
            if start_week <= week <= end_week:
                return True
        elif week >= start_week or week <= end_week:
            return True
    return False


def can_plant_crop_in_week(crop, week):
    return is_week_in_intervals(
        week, get_crop_week_intervals(crop, "planting_weeks"),
    )


def can_harvest_crop_in_week(crop, week):
    return is_week_in_intervals(
        week, get_crop_week_intervals(crop, "harvest_weeks"),
    )


def get_late_harvest_weeks_remaining(crop, week):
    """A rendes időablak utáni két póthétből hátralévő időt adja."""
    intervals = get_crop_week_intervals(crop, "harvest_weeks")
    if not intervals or can_harvest_crop_in_week(crop, week):
        return 0
    for _start_week, end_week in intervals:
        weeks_after_end = (week - end_week - 1) % 52
        if weeks_after_end < LATE_HARVEST_DURATION_WEEKS:
            return LATE_HARVEST_DURATION_WEEKS - weeks_after_end
    return 0


def can_late_harvest_crop_in_week(crop, week):
    return get_late_harvest_weeks_remaining(crop, week) > 0


def get_harvest_opportunity_weeks_remaining(crop, week):
    """Az aktuális szezon utolsó pótaratási hetéig hátralévő idő."""
    intervals = get_crop_week_intervals(crop, "harvest_weeks")
    if not intervals:
        return None
    for start_week, end_week in intervals:
        if is_week_in_intervals(week, ((start_week, end_week),)):
            return (
                (end_week - week) % 52
                + LATE_HARVEST_DURATION_WEEKS
            )
    late_remaining = get_late_harvest_weeks_remaining(crop, week)
    return late_remaining - 1 if late_remaining else None


def next_harvest_stage_fits_current_season(crop, week, growth_weeks):
    """Adatvezérelten ellenőrzi, hogy a következő érés még belefér-e."""
    definition = get_crop_definition(crop)
    if not definition or not definition.get(
        "next_stage_requires_same_harvest_season", False,
    ):
        return True
    remaining = get_harvest_opportunity_weeks_remaining(crop, week)
    return remaining is not None and growth_weeks <= remaining


def format_crop_week_intervals(crop, interval_name):
    """A központi növényadat hétintervallumait rövid magyar szöveggé alakítja."""
    intervals = get_crop_week_intervals(crop, interval_name)
    if not intervals:
        return None
    return ", ".join(
        f"{start_week}–{end_week}. hét"
        for start_week, end_week in intervals
    )
