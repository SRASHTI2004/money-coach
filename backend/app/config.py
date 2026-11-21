"""Named tuning constants (thresholds, limits, timeouts) shared across modules."""

# --- request limits (API)
MAX_UPLOAD_BYTES = 8_000_000
ALLOWED_UPLOAD_EXT = frozenset({".csv", ".tsv", ".txt", ".pdf"})
MAX_PASTE_CHARS = 200_000
MAX_CHAT_CHARS = 1000
AI_REQUESTS_PER_MINUTE = 40

# --- Gemini
BREAKER_SECONDS = 45  # skip AI this long after a failure so fallbacks answer instantly
DEFAULT_TIMEOUT_MS = 20_000
CHAT_HISTORY_MESSAGES = 8
MAX_TOOL_ROUNDS = 6

# --- recurring / subscription detection
FIXED_AMOUNT_SPREAD = 0.05  # max (max-min)/median to call an amount fixed
PRICE_STEP = 0.02  # a step bigger than this between charges is a price change
PRICE_CHANGE_WINDOW_DAYS = 75  # only report price changes this recent
MIN_CADENCE_CONSISTENCY = 0.7  # share of gaps that must fit the cadence band
UNUSED_AFTER_DAYS = 45
CANCELLED_AFTER_CYCLES = 1.5
UPCOMING_WITHIN_DAYS = 3
MANDATE_CHANGE_RUPEES = 1.0  # ignore rounding differences between mandate and last charge

# --- nudges
DRIFT_TOLERANCE = 1.10  # projected spend above budget by more than 10% -> drift nudge
MIN_DAY_FOR_PACE = 5  # do not extrapolate the month before this day
SPIKE_RATIO = 1.4
MIN_SPIKE_BASE = 1000.0

# --- time maths
DAYS_PER_MONTH = 30.4375
