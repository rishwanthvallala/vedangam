"""Shared astrological constants (signs, nakshatras, lordships, dignities)."""

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
SIGN_SHORT = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"]
SIGN_SANSKRIT = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula",
                 "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"]

ELEMENT = ["Fire", "Earth", "Air", "Water"] * 3
MODALITY = ["Cardinal", "Fixed", "Mutable"] * 4

# Vedic graha set (order used everywhere for Vedic tables)
GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
SEVEN = GRAHAS[:7]
GRAHA_SHORT = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju",
               "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke",
               "Uranus": "Ur", "Neptune": "Ne", "Pluto": "Pl", "Lagna": "As"}

SIGN_LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
             "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
# Co-lords used by Jaimini (Scorpio: Mars+Ketu, Aquarius: Saturn+Rahu)
CO_LORD = {7: "Ketu", 10: "Rahu"}

NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
              "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
              "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
              "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana",
              "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
NAK_SPAN = 360.0 / 27.0           # 13°20'
PADA_SPAN = NAK_SPAN / 4.0        # 3°20'

# Vimshottari
DASHA_ORDER = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
               "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}
NAK_LORD = [DASHA_ORDER[i % 9] for i in range(27)]

# Dignities (sidereal)
EXALTATION = {"Sun": (0, 10), "Moon": (1, 3), "Mars": (9, 28), "Mercury": (5, 15),
              "Jupiter": (3, 5), "Venus": (11, 27), "Saturn": (6, 20),
              "Rahu": (1, 20), "Ketu": (7, 20)}
DEBILITATION = {p: ((s + 6) % 12, d) for p, (s, d) in EXALTATION.items()}
# Moolatrikona sign and degree range
MOOLATRIKONA = {"Sun": (4, 0, 20), "Moon": (1, 4, 30), "Mars": (0, 0, 12),
                "Mercury": (5, 16, 20), "Jupiter": (8, 0, 10), "Venus": (6, 0, 15),
                "Saturn": (10, 0, 20), "Rahu": (2, 0, 30), "Ketu": (8, 0, 30)}
OWN_SIGNS = {"Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5], "Jupiter": [8, 11],
             "Venus": [1, 6], "Saturn": [9, 10], "Rahu": [10], "Ketu": [7]}

# Naisargika (natural) relationships, BPHS
FRIENDS = {
    "Sun": ["Moon", "Mars", "Jupiter"], "Moon": ["Sun", "Mercury"],
    "Mars": ["Sun", "Moon", "Jupiter"], "Mercury": ["Sun", "Venus"],
    "Jupiter": ["Sun", "Moon", "Mars"], "Venus": ["Mercury", "Saturn"],
    "Saturn": ["Mercury", "Venus"], "Rahu": ["Mercury", "Venus", "Saturn"],
    "Ketu": ["Mars", "Venus", "Saturn"],
}
ENEMIES = {
    "Sun": ["Venus", "Saturn"], "Moon": [], "Mars": ["Mercury"], "Mercury": ["Moon"],
    "Jupiter": ["Mercury", "Venus"], "Venus": ["Sun", "Moon"], "Saturn": ["Sun", "Moon", "Mars"],
    "Rahu": ["Sun", "Moon", "Mars"], "Ketu": ["Sun", "Moon"],
}

NATURAL_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
NATURAL_MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

# Combustion orbs (degrees from Sun); retrograde values in second slot
COMBUST_ORB = {"Moon": (12, 12), "Mars": (17, 17), "Mercury": (14, 12),
               "Jupiter": (11, 11), "Venus": (10, 8), "Saturn": (15, 15)}

WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
WEEKDAY_LORD = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
HORA_SEQ = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]  # Chaldean descending

TITHIS = ["Shukla Pratipada", "Shukla Dwitiya", "Shukla Tritiya", "Shukla Chaturthi",
          "Shukla Panchami", "Shukla Shashthi", "Shukla Saptami", "Shukla Ashtami",
          "Shukla Navami", "Shukla Dashami", "Shukla Ekadashi", "Shukla Dwadashi",
          "Shukla Trayodashi", "Shukla Chaturdashi", "Purnima",
          "Krishna Pratipada", "Krishna Dwitiya", "Krishna Tritiya", "Krishna Chaturthi",
          "Krishna Panchami", "Krishna Shashthi", "Krishna Saptami", "Krishna Ashtami",
          "Krishna Navami", "Krishna Dashami", "Krishna Ekadashi", "Krishna Dwadashi",
          "Krishna Trayodashi", "Krishna Chaturdashi", "Amavasya"]
YOGAS = ["Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma",
         "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
         "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha",
         "Shukla", "Brahma", "Indra", "Vaidhriti"]
KARANAS_MOVABLE = ["Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti"]

# Nakshatra attributes (for Avakahada chakra)
NAK_GANA = ["Deva", "Manushya", "Rakshasa", "Manushya", "Deva", "Manushya", "Deva", "Deva",
            "Rakshasa", "Rakshasa", "Manushya", "Manushya", "Deva", "Rakshasa", "Deva",
            "Rakshasa", "Deva", "Rakshasa", "Rakshasa", "Manushya", "Manushya", "Deva",
            "Rakshasa", "Rakshasa", "Manushya", "Manushya", "Deva"]
NAK_YONI = ["Horse", "Elephant", "Sheep", "Serpent", "Serpent", "Dog", "Cat", "Sheep", "Cat",
            "Rat", "Rat", "Cow", "Buffalo", "Tiger", "Buffalo", "Tiger", "Deer", "Deer", "Dog",
            "Monkey", "Mongoose", "Monkey", "Lion", "Horse", "Lion", "Cow", "Elephant"]
NAK_NADI = ["Adi", "Madhya", "Antya", "Antya", "Madhya", "Adi", "Adi", "Madhya", "Antya",
            "Antya", "Madhya", "Adi", "Adi", "Madhya", "Antya", "Antya", "Madhya", "Adi",
            "Adi", "Madhya", "Antya", "Antya", "Madhya", "Adi", "Adi", "Madhya", "Antya"]
SIGN_VARNA = ["Kshatriya", "Vaishya", "Shudra", "Brahmin"] * 3
SIGN_VASHYA = ["Chatushpada", "Chatushpada", "Manava", "Jalachara", "Vanachara", "Manava",
               "Manava", "Keeta", "Manava/Chatushpada", "Chatushpada/Jalachara", "Manava",
               "Jalachara"]
# Syllables (Namakshar) per pada
NAK_SYLLABLES = [
    ["Chu", "Che", "Cho", "La"], ["Li", "Lu", "Le", "Lo"], ["A", "I", "U", "E"],
    ["O", "Va", "Vi", "Vu"], ["Ve", "Vo", "Ka", "Ki"], ["Ku", "Gha", "Ng", "Chha"],
    ["Ke", "Ko", "Ha", "Hi"], ["Hu", "He", "Ho", "Da"], ["Di", "Du", "De", "Do"],
    ["Ma", "Mi", "Mu", "Me"], ["Mo", "Ta", "Ti", "Tu"], ["Te", "To", "Pa", "Pi"],
    ["Pu", "Sha", "Na", "Tha"], ["Pe", "Po", "Ra", "Ri"], ["Ru", "Re", "Ro", "Ta"],
    ["Ti", "Tu", "Te", "To"], ["Na", "Ni", "Nu", "Ne"], ["No", "Ya", "Yi", "Yu"],
    ["Ye", "Yo", "Bha", "Bhi"], ["Bhu", "Dha", "Pha", "Dha"], ["Bhe", "Bho", "Ja", "Ji"],
    ["Ju", "Je", "Jo", "Gha"], ["Ga", "Gi", "Gu", "Ge"], ["Go", "Sa", "Si", "Su"],
    ["Se", "So", "Da", "Di"], ["Du", "Tha", "Jha", "Na"], ["De", "Do", "Cha", "Chi"],
]

# Telugu namakshara for the same padas
NAK_SYLLABLES_TE = [
    ["చూ", "చే", "చో", "లా"], ["లీ", "లూ", "లే", "లో"], ["అ", "ఇ", "ఉ", "ఏ"],
    ["ఓ", "వా", "వీ", "వూ"], ["వే", "వో", "కా", "కీ"], ["కూ", "ఘ", "ఙ", "ఛ"],
    ["కే", "కో", "హా", "హీ"], ["హూ", "హే", "హో", "డా"], ["డీ", "డూ", "డే", "డో"],
    ["మా", "మీ", "మూ", "మే"], ["మో", "టా", "టీ", "టూ"], ["టే", "టో", "పా", "పీ"],
    ["పూ", "ష", "ణ", "ఠ"], ["పే", "పో", "రా", "రీ"], ["రూ", "రే", "రో", "తా"],
    ["తీ", "తూ", "తే", "తో"], ["నా", "నీ", "నూ", "నే"], ["నో", "యా", "యీ", "యూ"],
    ["యే", "యో", "భా", "భీ"], ["భూ", "ధా", "ఫా", "ఢా"], ["భే", "భో", "జా", "జీ"],
    ["జూ", "జే", "జో", "ఘ"], ["గా", "గీ", "గూ", "గే"], ["గో", "సా", "సీ", "సూ"],
    ["సే", "సో", "దా", "దీ"], ["దూ", "థ", "ఝ", "ఞ"], ["దే", "దో", "చా", "చీ"],
]

HOUSE_NAMES = ["Tanu", "Dhana", "Sahaja", "Sukha", "Putra", "Ari", "Yuvati", "Randhra",
               "Dharma", "Karma", "Labha", "Vyaya"]


def norm(x: float) -> float:
    x = x % 360.0
    return x + 360.0 if x < 0 else x


def sign_of(lon: float) -> int:
    return int(norm(lon) // 30) % 12


def deg_in_sign(lon: float) -> float:
    return norm(lon) % 30.0


def dms(x: float, sec: bool = True) -> str:
    """Degrees → D°MM'SS\" (always positive input expected)."""
    neg = x < 0
    x = abs(x)
    d = int(x)
    m_f = (x - d) * 60
    m = int(m_f)
    s = round((m_f - m) * 60)
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        d += 1
    out = f"{d}°{m:02d}'" + (f"{s:02d}\"" if sec else "")
    return ("-" if neg else "") + out


def sign_dms(lon: float) -> str:
    lon = norm(lon)
    return f"{dms(deg_in_sign(lon))} {SIGN_SHORT[sign_of(lon)]}"


def nakshatra_of(lon: float):
    lon = norm(lon)
    idx = int(lon // NAK_SPAN) % 27
    pada = int((lon % NAK_SPAN) // PADA_SPAN) + 1
    return idx, pada


def house_from(sign_a: int, sign_b: int) -> int:
    """House number of sign_b counted from sign_a (1..12)."""
    return (sign_b - sign_a) % 12 + 1
