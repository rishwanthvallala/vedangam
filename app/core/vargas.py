"""Shodashavarga (16 divisional charts) per Brihat Parashara Hora Shastra."""
from .constants import norm

VARGA_NAMES = {
    1: "Rasi (D1) – body, overall life", 2: "Hora (D2) – wealth",
    3: "Drekkana (D3) – siblings, courage", 4: "Chaturthamsa (D4) – property, fortune",
    7: "Saptamsa (D7) – children", 9: "Navamsa (D9) – spouse, dharma, inner strength",
    10: "Dasamsa (D10) – career, status", 12: "Dwadasamsa (D12) – parents",
    16: "Shodasamsa (D16) – vehicles, comforts", 20: "Vimsamsa (D20) – spiritual progress",
    24: "Chaturvimsamsa (D24) – education, learning", 27: "Bhamsa (D27) – strengths & weaknesses",
    30: "Trimsamsa (D30) – misfortunes, health", 40: "Khavedamsa (D40) – maternal legacy",
    45: "Akshavedamsa (D45) – paternal legacy, character", 60: "Shashtiamsa (D60) – past karma",
}
VARGAS = list(VARGA_NAMES.keys())

# Additional (non-Shodashavarga) divisions shown by Parashara's Light / Jagannatha Hora
EXTRA_VARGA_NAMES = {
    5: "Panchamsa (D5) – fame, power", 6: "Shashtamsa (D6) – health, disease",
    8: "Ashtamsa (D8) – sudden events, longevity", 11: "Rudramsa (D11) – gains, destruction",
    81: "Nava-navamsa (D81) – subtle karma", 108: "Ashtottaramsa (D108) – auspiciousness, past merit",
    144: "Dwadas-dwadasamsa (D144) – fine timing", 150: "Nadiamsa (D150) – nadi-level detail",
}
EXTRA_VARGAS = list(EXTRA_VARGA_NAMES.keys())


def varga_sign(lon: float, n: int) -> int:
    lon = norm(lon)
    s = int(lon // 30)
    d = lon % 30
    odd = s % 2 == 0          # Aries (0) is an odd sign
    mov, fix = s % 3 == 0, s % 3 == 1
    if n == 1:
        return s
    if n == 2:  # Parashara hora: Sun (Leo) / Moon (Cancer)
        first = d < 15
        return (4 if first else 3) if odd else (3 if first else 4)
    if n == 3:
        return (s + 4 * int(d // 10)) % 12
    if n == 4:
        return (s + 3 * int(d // 7.5)) % 12
    if n == 7:
        part = int(d // (30 / 7))
        return (s + part) % 12 if odd else (s + 6 + part) % 12
    if n == 9:
        return int(lon // (10 / 3)) % 12
    if n == 10:
        part = int(d // 3)
        return (s + part) % 12 if odd else (s + 8 + part) % 12
    if n == 12:
        return (s + int(d // 2.5)) % 12
    if n == 16:
        start = 0 if mov else (4 if fix else 8)
        return (start + int(d // (30 / 16))) % 12
    if n == 20:
        start = 0 if mov else (8 if fix else 4)
        return (start + int(d // 1.5)) % 12
    if n == 24:
        start = 4 if odd else 3
        return (start + int(d // 1.25)) % 12
    if n == 27:
        return int(lon // (30 / 27)) % 12
    if n == 30:
        if odd:
            bounds = [(5, 0), (10, 10), (18, 8), (25, 2), (30, 6)]
        else:
            bounds = [(5, 1), (12, 5), (20, 11), (25, 9), (30, 7)]
        for lim, sg in bounds:
            if d < lim:
                return sg
        return bounds[-1][1]
    if n == 40:
        start = 0 if odd else 6
        return (start + int(d // 0.75)) % 12
    if n == 45:
        start = 0 if mov else (4 if fix else 8)
        return (start + int(d // (30 / 45))) % 12
    if n == 60:
        return (s + int(d * 2)) % 12
    if n == 5:   # Parashari panchamsa: odd Ar,Aq,Sg,Ge,Li / even Ta,Vi,Pi,Cp,Sc
        part = min(int(d // 6), 4)
        return [0, 10, 8, 2, 6][part] if odd else [1, 5, 11, 9, 7][part]
    if n == 6:   # odd from Aries, even from Libra
        return ((0 if odd else 6) + int(d // 5)) % 12
    if n == 8:   # movable from Aries, fixed from Sagittarius, dual from Leo
        start = 0 if mov else (8 if fix else 4)
        return (start + int(d // 3.75)) % 12
    if n == 11:  # Rudramsa, cyclical (Parivritti) from Aries
        return int(lon // (30 / 11)) % 12
    if n == 81:  # navamsa of navamsa
        return int(lon // (30 / 81)) % 12
    if n == 108:  # Ashtottaramsa: cyclical 108 parts, i.e. the D12 of each navamsa
        return int(lon // (30 / 108)) % 12
    if n == 144:  # D12 of the D12 longitude
        d12 = (s + int(d // 2.5)) % 12 * 30 + (d % 2.5) * 12
        return varga_sign(d12, 12)
    if n == 150:  # Nadiamsa: 0°12' parts, forward from the sign in odd signs, backward in even
        part = int(d // 0.2)
        return (s + part) % 12 if odd else (s - part) % 12
    raise ValueError(f"unsupported varga D{n}")


def varga_lon(lon: float, n: int) -> float:
    """Longitude inside the divisional sign (degree within varga sign scaled)."""
    d = (norm(lon) % 30) * n % 30
    return varga_sign(lon, n) * 30 + d


PUSHKAR_BHAGA = [21, 14, 18, 8, 19, 9, 24, 11, 23, 14, 19, 9]   # degree per sign (Ar..Pi)
# Pushkar navamsas (navamsa index 1..9 within the sign) by element: fire 7,9; earth 3,5; air 6,8; water 1,3
PUSHKAR_NAVAMSA = {0: (7, 9), 1: (3, 5), 2: (6, 8), 3: (1, 3)}


def pushkar(lon: float) -> dict:
    lon = norm(lon)
    s, d = int(lon // 30), lon % 30
    nav = int(d // (10 / 3)) + 1
    in_nav = nav in PUSHKAR_NAVAMSA[s % 4]
    in_bhaga = abs(d - PUSHKAR_BHAGA[s]) < 1.0
    return {"pushkar_navamsa": in_nav, "pushkar_bhaga": in_bhaga}


# D60 shashtiamsa deity names (odd signs; even signs reversed)
D60_DEITIES = ["Ghora", "Rakshasa", "Deva", "Kubera", "Yaksha", "Kinnara", "Bhrashta",
               "Kulaghna", "Garala", "Vahni", "Maya", "Purishaka", "Apampati", "Marutwan",
               "Kaala", "Sarpa", "Amrita", "Indu", "Mridu", "Komala", "Heramba", "Brahma",
               "Vishnu", "Maheshwara", "Deva", "Ardra", "Kalinasa", "Kshitiswara",
               "Kamalakara", "Gulika", "Mrityu", "Kaala", "Davagni", "Ghora", "Yama",
               "Kantaka", "Sudha", "Amrita", "Purnachandra", "Vishadagdha", "Kulanasa",
               "Vamshakshaya", "Utpata", "Kaala", "Saumya", "Komala", "Sheetala",
               "Karaladamshtra", "Chandramukhi", "Praveena", "Kaalpavaka", "Dandayudha",
               "Nirmala", "Saumya", "Kroora", "Atisheetala", "Amrita", "Payodhi",
               "Bhramana", "Chandrarekha"]
D60_BENEFIC = {2, 3, 4, 5, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 27, 28, 36, 37, 38, 43,
               44, 45, 46, 48, 49, 51, 52, 55, 56, 58, 59}


def d60_deity(lon: float):
    lon = norm(lon)
    s = int(lon // 30)
    idx = int((lon % 30) * 2)
    if s % 2 == 1:
        idx = 59 - idx
    return D60_DEITIES[idx], idx in D60_BENEFIC
