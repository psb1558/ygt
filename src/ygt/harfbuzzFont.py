from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QDialogButtonBox, QComboBox, QLineEdit
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression, pyqtSlot
import uharfbuzz as hb
from tempfile import SpooledTemporaryFile
from .freetypeFont import freetypeFont


class harfbuzzFont:
    LANG_DEFAULT = 0xFFFF

    SCRIPT_DEFAULT = 0

    DEFAULT_LAYOUT_TAGS = [
        "ccmp",
        "liga",
        "calt",
        "rlig",
        "locl"
    ]

    # We omit cvNN and ssNN tags, but instead construct these when needed.
    LAYOUT_TAGS = {
        "abvf": "Above-base Forms",
        "abvm": "Above-base Mark Positioning",
        "abvs": "Above-base Substitutions",
        "blwf": "Below-base Forms",
        "blwm": "Below-base Mark Positioning",
        "blws": "Below-base Substitutions",
        "pref": "Pre-base Forms",
        "pres": "Pre-base Substitutions",
        "psts": "Post-base Substitutions",
        "pstf": "Post-base Forms",
        "dist": "Distance",
        "akhn": "Akhand",
        "haln": "Halant Forms",
        "half": "Half Form",
        "nukt": "Nukta Forms",
        "rkrf": "Rakar Forms",
        "rphf": "Reph Form",
        "vatu": "Vattu Variants",
        "cjct": "Conjunct Forms",
        "cfar": "Conjunct Form After Ro",
        "smpl": "Simplified Forms",
        "trad": "Traditional Forms",
        "tnam": "Traditional Name Forms",
        "expt": "Expert Forms",
        "hojo": "Hojo Kanji Forms",
        "nlck": "NLC Kanji Forms",
        "jp78": "JIS 78 Forms",
        "jp83": "JIS 83 Forms",
        "jp90": "JIS 90 Forms",
        "jp04": "JIS 04 Forms",
        "hngl": "Hangul",
        "ljmo": "Leading Jamo Forms",
        "tjmo": "Trailing Jamo Forms",
        "vjmo": "Vowel Jamo Forms",
        "fwid": "Full Widths",
        "hwid": "Half Widths",
        "halt": "Alternate Half Widths",
        "twid": "Third Widths",
        "qwid": "Quarter Widths",
        "pwid": "Proportional Widths",
        "palt": "Proportional Alternates",
        "pkna": "Proportional Kana",
        "ruby": "Ruby Notation Forms",
        "hkna": "Horizontal Kana Alternates",
        "vkna": "Vertical Kana",
        "cpct": "Centered CJK Punctuation",
        "curs": "Cursive Positioning",
        "jalt": "Justification Alternates",
        "mset": "Mark Positioning via Substitution",
        "rclt": "Required Contextual Alternates",
        "rlig": "Required Ligatures",
        "isol": "Isolated Forms",
        "init": "Initial Forms",
        "medi": "Medial Forms",
        "med2": "Medial Form #2",
        "fina": "Terminal Forms",
        "fin2": "Terminal Form #2",
        "fin3": "Terminal Form #3",
        "falt": "Final Glyph on Line Alternates",
        "stch": "Stretching Glyph Decomposition",
        "smcp": "Small Caps",
        "c2sc": "Capitals to Small Caps",
        "pcap": "Petite Caps",
        "c2pc": "Capitals to Petite Caps",
        "unic": "Unicase",
        "cpsp": "Capital Spacing",
        "case": "Case Sensitive Forms",
        "ital": "Italics",
        "ordn": "Ordinals",
        "valt": "Alternative Vertical Metrics",
        "vhal": "Alternative Vertical Half Metrics",
        "vpal": "Proportional Alternate Vertical Metrics",
        "vert": "Vertical Alternates",
        "vrt2": "Vertical Alternates and Rotation",
        "vrtr": "Vertical Alternates for Rotation",
        "vkrn": "Vertical Kerning",
        "ltra": "Left-to-right glyph alternates",
        "ltrm": "Left-to-right mirrored forms",
        "rtla": "Right-to-left glyph alternates",
        "rtlm": "Right-to-left mirrored forms",
        "lnum": "Lining Figures",
        "onum": "Oldstyle Figures",
        "pnum": "Proportional Figures",
        "tnum": "Tabular Figures",
        "frac": "Fractions",
        "afrc": "Alternative Fractions",
        "dnom": "Denominator",
        "numr": "Numerator",
        "sinf": "Scientific Inferiors",
        "zero": "Slashed Zero",
        "mgrk": "Mathematical Greek",
        "flac": "Flattened accent forms",
        "dtls": "Dotless Forms",
        "ssty": "Math script style alternates",
        "aalt": "Access All Alternates",
        "swsh": "Swash",
        "cswh": "Contextual Swash",
        "calt": "Contextual Alternates",
        "hist": "Historical Forms",
        "locl": "Localized Forms",
        "rand": "Randomize",
        "nalt": "Alternate Annotation Forms",
        "salt": "Stylistic Alternates",
        "subs": "Subscript",
        "sups": "Superscript",
        "titl": "Titling Alternates",
        "rvrn": "Required Variation Alternates",
        "clig": "Contextual Ligatures",
        "dlig": "Discretionary Ligatures",
        "hlig": "Historical Ligatures",
        "liga": "Standard Ligatures",
        "ccmp": "Glyph Composition/Decomposition",
        "kern": "Kerning",
        "mark": "Mark Positioning",
        "mkmk": "Mark-to-mark Positioning",
        "opbd": "Optical Bounds",
        "lfbd": "Left Bounds",
        "rtbd": "Right Bounds",
        "ornm": "Ornaments",
    }

    SCRIPT_TAGS = {
        'adlm': "Adlam",
        'ahom': "Ahom",
        'hluw': "Anatolian Hieroglyphs",
        'arab': "Arabic",
        'armn': "Armenian",
        'avst': "Avestan",
        'bali': "Balinese",
        'bamu': "Bamum",
        'bass': "Bassa Vah",
        'batk': "Batak",
        'beng': "Bengali",
        'bng2': "Bengali v.2",
        'bhks': "Bhaiksuki",
        'bopo': "Bopomofo",
        'brah': "Brahmi",
        'brai': "Braille",
        'bugi': "Buginese",
        'buhd': "Buhid",
        'byzm': "Byzantine Music",
        'cans': "Canadian Syllabics",
        'cari': "Carian",
        'aghb': "Caucasian Albanian",
        'cakm': "Chakma",
        'cham': "Cham",
        'cher': "Cherokee",
        'chrs': "Chorasmian",
        'hani': "CJK Ideographic",
        'copt': "Coptic",
        'cprt': "Cypriot Syllabary",
        'cpmn': "Cypro-Minoan",
        'cyrl': "Cyrillic",
        'DFLT': "Default",
        'dsrt': "Deseret",
        'deva': "Devanagari",
        'dev2': "Devanagari v.2",
        'diak': "Dives Akuru",
        'dogr': "Dogra",
        'dupl': "Duployan",
        'egyp': "Egyptian Hieroglyphs",
        'elba': "Elbasan",
        'elym': "Elymaic",
        'ethi': "Ethiopic",
        'geor': "Georgian",
        'glag': "Glagolitic",
        'goth': "Gothic",
        'gran': "Grantha",
        'grek': "Greek",
        'gujr': "Gujarati",
        'gjr2': "Gujarati v.2",
        'gong': "Gunjala Gondi",
        'guru': "Gurmukhi",
        'gur2': "Gurmukhi v.2",
        'hang': "Hangul",
        'jamo': "Hangul Jamo",
        'rohg': "Hanifi Rohingya",
        'hano': "Hanunoo",
        'hatr': "Hatran",
        'hebr': "Hebrew",
        'kana': "Hiragana",
        'armi': "Imperial Aramaic",
        'phli': "Inscriptional Pahlavi",
        'prti': "Inscriptional Parthian",
        'java': "Javanese",
        'kthi': "Kaithi",
        'knda': "Kannada",
        'knd2': "Kannada v.2",
        'kana': "Katakana",
        'kali': "Kayah Li",
        'khar': "Kharosthi",
        'kits': "Khitan Small Script",
        'khmr': "Khmer",
        'khoj': "Khojki",
        'sind': "Khudawadi",
        'lao ': "Lao",
        'latn': "Latin",
        'lepc': "Lepcha",
        'limb': "Limbu",
        'lina': "Linear A",
        'linb': "Linear B",
        'lisu': "Lisu (Fraser)",
        'lyci': "Lycian",
        'lydi': "Lydian",
        'mahj': "Mahajani",
        'maka': "Makasar",
        'mlym': "Malayalam",
        'mlm2': "Malayalam v.2",
        'mand': "Mandaic, Mandaean",
        'mani': "Manichaean",
        'marc': "Marchen",
        'gonm': "Masaram Gondi",
        'math': "Mathematical Alphanumeric Symbols",
        'medf': "Medefaidrin (Oberi Okaime, Oberi Ɔkaimɛ)",
        'mtei': "Meitei Mayek (Meithei, Meetei)",
        'mend': "Mende Kikakui",
        'merc': "Meroitic Cursive",
        'mero': "Meroitic Hieroglyphs",
        'plrd': "Miao",
        'modi': "Modi",
        'mong': "Mongolian",
        'mroo': "Mro",
        'mult': "Multani",
        'musc': "Musical Symbols",
        'mymr': "Myanmar",
        'mym2': "Myanmar v.2",
        'nbat': "Nabataean",
        'nand': "Nandinagari",
        'newa': "Newa",
        'talu': "New Tai Lue",
        'nko ': "N'Ko",
        'nshu': "Nüshu",
        'hmnp': "Nyiakeng Puachue Hmong",
        'orya': "Odia (formerly Oriya)",
        'ory2': "Odia v.2 (formerly Oriya v.2)",
        'ogam': "Ogham",
        'olck': "Ol Chiki",
        'ital': "Old Italic",
        'hung': "Old Hungarian",
        'narb': "Old North Arabian",
        'perm': "Old Permic",
        'xpeo': "Old Persian Cuneiform",
        'sogo': "Old Sogdian",
        'sarb': "Old South Arabian",
        'orkh': "Old Turkic, Orkhon Runic",
        'ougr': "Old Uyghur",
        'osge': "Osage",
        'osma': "Osmanya",
        'hmng': "Pahawh Hmong",
        'palm': "Palmyrene",
        'pauc': "Pau Cin Hau",
        'phag': "Phags-pa",
        'phnx': "Phoenician",
        'phlp': "Psalter Pahlavi",
        'rjng': "Rejang",
        'runr': "Runic",
        'samr': "Samaritan",
        'saur': "Saurashtra",
        'shrd': "Sharada",
        'shaw': "Shavian",
        'sidd': "Siddham",
        'sgnw': "Sign Writing",
        'sinh': "Sinhala",
        'sogd': "Sogdian",
        'sora': "Sora Sompeng",
        'soyo': "Soyombo",
        'xsux': "Sumero-Akkadian Cuneiform",
        'sund': "Sundanese",
        'sylo': "Syloti Nagri",
        'syrc': "Syriac",
        'tglg': "Tagalog",
        'tagb': "Tagbanwa",
        'tale': "Tai Le",
        'lana': "Tai Tham (Lanna)",
        'tavt': "Tai Viet",
        'takr': "Takri",
        'taml': "Tamil",
        'tml2': "Tamil v.2",
        'tnsa': "Tangsa",
        'tang': "Tangut",
        'telu': "Telugu",
        'tel2': "Telugu v.2",
        'thaa': "Thaana",
        'thai': "Thai",
        'tibt': "Tibetan",
        'tfng': "Tifinagh",
        'tirh': "Tirhuta",
        'toto': "Toto",
        'ugar': "Ugaritic Cuneiform",
        'vai ': "Vai",
        'vith': "Vithkuqi",
        'wcho': "Wancho",
        'wara': "Warang Citi",
        'yezi': "Yezidi",
        'yi  ': "Yi",
        'zanb': "Zanabazar Square",
    }

    LANGUAGE_TAGS = {
        'ABA ': "Abaza",
        'ABK ': "Abkhazian",
        'ACH ': "Acholi",
        'ACR ': "Achi",
        'ADY ': "Adyghe",
        'AFK ': "Afrikaans",
        'AFR ': "Afar",
        'AGW ': "Agaw",
        'AIO ': "Aiton",
        'AKA ': "Akan",
        'AKB ': "Batak Angkola",
        'ALS ': "Alsatian",
        'ALT ': "Altai",
        'AMH ': "Amharic",
        'ANG ': "Anglo-Saxon",
        'ARA ': "Arabic",
        'ARG ': "Aragonese",
        'ARI ': "Aari",
        'ARK ': "Rakhine",
        'ASM ': "Assamese",
        'AST ': "Asturian",
        'ATH ': "Athapaskan languages",
        'AVN ': "Avatime",
        'AVR ': "Avar",
        'AWA ': "Awadhi",
        'AYM ': "Aymara",
        'AZB ': "Torki",
        'AZE ': "Azerbaijani",
        'BAD ': "Badaga",
        'BAG ': "Baghelkhandi",
        'BAL ': "Balkar",
        'BAN ': "Balinese",
        'BAR ': "Bavarian",
        'BAU ': "Baulé",
        'BBC ': "Batak Toba",
        'BBR ': "Berber",
        'BCH ': "Bench",
        'BCR ': "Bible Cree",
        'BDY ': "Bandjalang",
        'BEL ': "Belarussian",
        'BEM ': "Bemba",
        'BEN ': "Bengali",
        'BGC ': "Haryanvi",
        'BGQ ': "Bagri",
        'BGR ': "Bulgarian",
        'BHI ': "Bhili",
        'BHO ': "Bhojpuri",
        'BIK ': "Bikol",
        'BIL ': "Bilen",
        'BIS ': "Bislama",
        'BJJ ': "Kanauji",
        'BKF ': "Blackfoot",
        'BLI ': "Baluchi",
        'BLK ': "Pa’o Karen",
        'BLN ': "Balante",
        'BLT ': "Balti",
        'BMB ': "Bambara (Bamanankan)",
        'BML ': "Bamileke",
        'BOS ': "Bosnian",
        'BPY ': "Bishnupriya Manipuri",
        'BRE ': "Breton",
        'BRH ': "Brahui",
        'BRI ': "Braj Bhasha",
        'BRM ': "Burmese",
        'BRX ': "Bodo",
        'BSH ': "Bashkir",
        'BSK ': "Burushaski",
        'BTD ': "Batak Dairi (Pakpak)",
        'BTI ': "Beti",
        'BTK ': "Batak languages",
        'BTM ': "Batak Mandailing",
        'BTS ': "Batak Simalungun",
        'BTX ': "Batak Karo",
        'BTZ ': "Batak Alas-Kluet",
        'BUG ': "Bugis",
        'BYV ': "Medumba",
        'CAK ': "Kaqchikel",
        'CAT ': "Catalan",
        'CBK ': "Zamboanga Chavacano",
        'CEB ': "Cebuano",
        'CGG ': "Chiga",
        'CHA ': "Chamorro",
        'CHE ': "Chechen",
        'CHG ': "Chaha Gurage",
        'CHH ': "Chattisgarhi",
        'CHI ': "Chichewa (Chewa, Nyanja)",
        'CHK ': "Chukchi",
        'CHO ': "Choctaw",
        'CHP ': "Chipewyan",
        'CHR ': "Cherokee",
        'CHU ': "Chuvash",
        'CHY ': "Cheyenne",
        'CJA ': "Western Cham",
        'CJM ': "Eastern Cham",
        'CMR ': "Comorian",
        'COP ': "Coptic",
        'COR ': "Cornish",
        'COS ': "Corsican",
        'CPP ': "Creoles",
        'CRE ': "Cree",
        'CRR ': "Carrier",
        'CRT ': "Crimean Tatar",
        'CSB ': "Kashubian",
        'CSL ': "Church Slavonic",
        'CSY ': "Czech",
        'CTG ': "Chittagonian",
        'CTT ': "Wayanad Chetti",
        'CUK ': "San Blas Kuna",
        'DAG ': "Dagbani",
        'DAN ': "Danish",
        'DAR ': "Dargwa",
        'DAX ': "Dayi",
        'DCR ': "Woods Cree",
        'DEU ': "German",
        'DGO ': "Dogri (individual language)",
        'DGR ': "Dogri (macrolanguage)",
        'DHG ': "Dhangu",
        'DHV ': "Divehi (Dhivehi, Maldivian)",
        'DIQ ': "Dimli",
        'DIV ': "Divehi (Dhivehi, Maldivian)",
        'DJR ': "Zarma",
        'DNG ': "Dangme",
        'DNJ ': "Dan",
        'DNK ': "Dinka",
        'DRI ': "Dari",
        'DUJ ': "Dhuwal",
        'DUN ': "Dungan",
        'DZN ': "Dzongkha",
        'EBI ': "Ebira",
        'ECR ': "Eastern Cree",
        'EDO ': "Edo",
        'EFI ': "Efik",
        'ELL ': "Greek",
        'EMK ': "Eastern Maninkakan",
        'ENG ': "English",
        'ERZ ': "Erzya",
        'ESP ': "Spanish",
        'ESU ': "Central Yupik",
        'ETI ': "Estonian",
        'EUQ ': "Basque",
        'EVK ': "Evenki",
        'EVN ': "Even",
        'EWE ': "Ewe",
        'FAN ': "French Antillean",
        'FAR ': "Persian",
        'FAT ': "Fanti",
        'FIN ': "Finnish",
        'FJI ': "Fijian",
        'FLE ': "Dutch (Flemish)",
        'FMP ': "Fe’fe’",
        'FNE ': "Forest Enets",
        'FON ': "Fon",
        'FOS ': "Faroese",
        'FRA ': "French",
        'FRC ': "Cajun French",
        'FRI ': "Frisian",
        'FRL ': "Friulian",
        'FRP ': "Arpitan",
        'FTA ': "Futa",
        'FUL ': "Fulah",
        'FUV ': "Nigerian Fulfulde",
        'GAD ': "Ga",
        'GAE ': "Scottish Gaelic (Gaelic)",
        'GAG ': "Gagauz",
        'GAL ': "Galician",
        'GAR ': "Garshuni",
        'GAW ': "Garhwali",
        'GEZ ': "Geez",
        'GIH ': "Githabul",
        'GIL ': "Gilyak",
        'GKP ': "Kpelle (Guinea)",
        'GLK ': "Gilaki",
        'GMZ ': "Gumuz",
        'GNN ': "Gumatj",
        'GOG ': "Gogo",
        'GON ': "Gondi",
        'GRN ': "Greenlandic",
        'GRO ': "Garo",
        'GUA ': "Guarani",
        'GUC ': "Wayuu",
        'GUF ': "Gupapuyngu",
        'GUJ ': "Gujarati",
        'GUZ ': "Gusii",
        'HAI ': "Haitian (Haitian Creole)",
        'HAI0': "Haida",
        'HAL ': "Halam (Falam Chin)",
        'HAR ': "Harauti",
        'HAU ': "Hausa",
        'HAW ': "Hawaiian",
        'HAY ': "Haya",
        'HAZ ': "Hazaragi",
        'HBN ': "Hammer-Banna",
        'HEI ': "Heiltsuk",
        'HER ': "Herero",
        'HIL ': "Hiligaynon",
        'HIN ': "Hindi",
        'HMA ': "High Mari",
        'HMD ': "A-Hmao",
        'HMN ': "Hmong",
        'HMO ': "Hiri Motu",
        'HMZ ': "Hmong Shuat",
        'HND ': "Hindko",
        'HO  ': "Ho",
        'HRI ': "Harari",
        'HRV ': "Croatian",
        'HUN ': "Hungarian",
        'HYE ': "Armenian",
        'IBA ': "Iban",
        'IBB ': "Ibibio",
        'IBO ': "Igbo",
        'IDO ': "Ido",
        'IJO ': "Ijo languages",
        'ILE ': "Interlingue",
        'ILO ': "Ilokano",
        'INA ': "Interlingua",
        'IND ': "Indonesian",
        'ING ': "Ingush",
        'INU ': "Inuktitut",
        'INUK': "Nunavik Inuktitut",
        'IPK ': "Inupiat",
        'IRI ': "Irish",
        'IRT ': "Irish Traditional",
        'IRU ': "Irula",
        'ISL ': "Icelandic",
        'ISM ': "Inari Sami",
        'ITA ': "Italian",
        'IWR ': "Hebrew",
        'JAM ': "Jamaican Creole",
        'JAN ': "Japanese",
        'JAV ': "Javanese",
        'JBO ': "Lojban",
        'JCT ': "Krymchak",
        'JII ': "Yiddish",
        'JUD ': "Ladino",
        'JUL ': "Jula",
        'KAB ': "Kabardian",
        'KAC ': "Kachchi",
        'KAL ': "Kalenjin",
        'KAN ': "Kannada",
        'KAR ': "Karachay",
        'KAT ': "Georgian",
        'KAW ': "Kawi (Old Javanese)",
        'KAZ ': "Kazakh",
        'KDE ': "Makonde",
        'KEA ': "Kabuverdianu (Crioulo)",
        'KEB ': "Kebena",
        'KEK ': "Kekchi",
        'KGE ': "Khutsuri Georgian",
        'KHA ': "Khakass",
        'KHK ': "Khanty-Kazim",
        'KHM ': "Khmer",
        'KHS ': "Khanty-Shurishkar",
        'KHT ': "Khamti Shan",
        'KHV ': "Khanty-Vakhi",
        'KHW ': "Khowar",
        'KIK ': "Kikuyu (Gikuyu)",
        'KIR ': "Kirghiz (Kyrgyz)",
        'KIS ': "Kisii",
        'KIU ': "Kirmanjki",
        'KJD ': "Southern Kiwai",
        'KJP ': "Eastern Pwo Karen",
        'KJZ ': "Bumthangkha",
        'KKN ': "Kokni",
        'KLM ': "Kalmyk",
        'KMB ': "Kamba",
        'KMN ': "Kumaoni",
        'KMO ': "Komo",
        'KMS ': "Komso",
        'KMZ ': "Khorasani Turkic",
        'KNR ': "Kanuri",
        'KOD ': "Kodagu",
        'KOH ': "Korean Old Hangul",
        'KOK ': "Konkani",
        'KOM ': "Komi",
        'KON ': "Kikongo",
        'KOP ': "Komi-Permyak",
        'KOR ': "Korean",
        'KOS ': "Kosraean",
        'KOZ ': "Komi-Zyrian",
        'KPL ': "Kpelle",
        'KRI ': "Krio",
        'KRK ': "Karakalpak",
        'KRL ': "Karelian",
        'KRM ': "Karaim",
        'KRN ': "Karen",
        'KRT ': "Koorete",
        'KSH ': "Kashmiri",
        'KSI ': "Khasi",
        'KSM ': "Kildin Sami",
        'KSW ': "S’gaw Karen",
        'KUA ': "Kuanyama",
        'KUI ': "Kui",
        'KUL ': "Kulvi",
        'KUM ': "Kumyk",
        'KUR ': "Kurdish",
        'KUU ': "Kurukh",
        'KUY ': "Kuy",
        'KWK ': "Kwakʼwala",
        'KYK ': "Koryak",
        'KYU ': "Western Kayah",
        'LAD ': "Ladin",
        'LAH ': "Lahuli",
        'LAK ': "Lak",
        'LAM ': "Lambani",
        'LAO ': "Lao",
        'LAT ': "Latin",
        'LAZ ': "Laz",
        'LCR ': "L-Cree",
        'LDK ': "Ladakhi",
        'LEF ': "Lelemi",
        'LEZ ': "Lezgi",
        'LIJ ': "Ligurian",
        'LIM ': "Limburgish",
        'LIN ': "Lingala",
        'LIS ': "Lisu",
        'LJP ': "Lampung",
        'LKI ': "Laki",
        'LMA ': "Low Mari",
        'LMB ': "Limbu",
        'LMO ': "Lombard",
        'LMW ': "Lomwe",
        'LOM ': "Loma",
        'LPO ': "Lipo",
        'LRC ': "Luri",
        'LSB ': "Lower Sorbian",
        'LSM ': "Lule Sami",
        'LTH ': "Lithuanian",
        'LTZ ': "Luxembourgish",
        'LUA ': "Luba-Lulua",
        'LUB ': "Luba-Katanga",
        'LUG ': "Ganda",
        'LUH ': "Luyia",
        'LUO ': "Luo",
        'LVI ': "Latvian",
        'MAD ': "Madura",
        'MAG ': "Magahi",
        'MAH ': "Marshallese",
        'MAJ ': "Majang",
        'MAK ': "Makhuwa",
        'MAL ': "Malayalam",
        'MAM ': "Mam",
        'MAN ': "Mansi",
        'MAP ': "Mapudungun",
        'MAR ': "Marathi",
        'MAW ': "Marwari",
        'MBN ': "Mbundu",
        'MBO ': "Mbo",
        'MCH ': "Manchu",
        'MCR ': "Moose Cree",
        'MDE ': "Mende",
        'MDR ': "Mandar",
        'MEN ': "Me’en",
        'MER ': "Meru",
        'MFA ': "Pattani Malay",
        'MFE ': "Morisyen",
        'MIN ': "Minangkabau",
        'MIZ ': "Mizo",
        'MKD ': "Macedonian",
        'MKR ': "Makasar",
        'MKW ': "Kituba",
        'MLE ': "Male",
        'MLG ': "Malagasy",
        'MLN ': "Malinke",
        'MLR ': "Malayalam Reformed",
        'MLY ': "Malay",
        'MND ': "Mandinka",
        'MNG ': "Mongolian",
        'MNI ': "Manipuri",
        'MNK ': "Maninka",
        'MNX ': "Manx",
        'MOH ': "Mohawk",
        'MOK ': "Moksha",
        'MOL ': "Moldavian",
        'MON ': "Mon",
        'MONT': "Thailand Mon",
        'MOR ': "Moroccan",
        'MOS ': "Mossi",
        'MRI ': "Maori",
        'MTH ': "Maithili",
        'MTS ': "Maltese",
        'MUN ': "Mundari",
        'MUS ': "Muscogee",
        'MWL ': "Mirandese",
        'MWW ': "Hmong Daw",
        'MYN ': "Mayan",
        'MZN ': "Mazanderani",
        'NAG ': "Naga-Assamese",
        'NAH ': "Nahuatl",
        'NAN ': "Nanai",
        'NAP ': "Neapolitan",
        'NAS ': "Naskapi",
        'NAU ': "Nauruan",
        'NAV ': "Navajo",
        'NCR ': "N-Cree",
        'NDB ': "Ndebele",
        'NDC ': "Ndau",
        'NDG ': "Ndonga",
        'NDS ': "Low Saxon",
        'NEP ': "Nepali",
        'NEW ': "Newari",
        'NGA ': "Ngbaka",
        'NGR ': "Nagari",
        'NHC ': "Norway House Cree",
        'NIS ': "Nisi",
        'NIU ': "Niuean",
        'NKL ': "Nyankole",
        'NKO ': "N’Ko",
        'NLD ': "Dutch",
        'NOE ': "Nimadi",
        'NOG ': "Nogai",
        'NOR ': "Norwegian",
        'NOV ': "Novial",
        'NSM ': "Northern Sami",
        'NSO ': "Northern Sotho",
        'NTA ': "Northern Tai",
        'NTO ': "Esperanto",
        'NYM ': "Nyamwezi",
        'NYN ': "Norwegian Nynorsk (Nynorsk, Norwegian)",
        'NZA ': "Mbembe Tigon",
        'OCI ': "Occitan",
        'OCR ': "Oji-Cree",
        'OJB ': "Ojibway",
        'ORI ': "Odia (formerly Oriya)",
        'ORO ': "Oromo",
        'OSS ': "Ossetian",
        'PAA ': "Palestinian Aramaic",
        'PAG ': "Pangasinan",
        'PAL ': "Pali",
        'PAM ': "Pampangan",
        'PAN ': "Punjabi",
        'PAP ': "Palpa",
        'PAS ': "Pashto",
        'PAU ': "Palauan",
        'PCC ': "Bouyei",
        'PCD ': "Picard",
        'PDC ': "Pennsylvania German",
        'PGR ': "Polytonic Greek",
        'PHK ': "Phake",
        'PIH ': "Norfolk",
        'PIL ': "Filipino",
        'PLG ': "Palaung",
        'PLK ': "Polish",
        'PMS ': "Piemontese",
        'PNB ': "Western Panjabi",
        'POH ': "Pocomchi",
        'PON ': "Pohnpeian",
        'PRO ': "Provençal / Old Provençal",
        'PTG ': "Portuguese",
        'PWO ': "Western Pwo Karen",
        'QIN ': "Chin",
        'QUC ': "K’iche’",
        'QUH ': "Quechua (Bolivia)",
        'QUZ ': "Quechua",
        'QVI ': "Quechua (Ecuador)",
        'QWH ': "Quechua (Peru)",
        'RAJ ': "Rajasthani",
        'RAR ': "Rarotongan",
        'RBU ': "Russian Buriat",
        'RCR ': "R-Cree",
        'REJ ': "Rejang",
        'RIA ': "Riang",
        'RHG ': "Rohingya",
        'RIF ': "Tarifit",
        'RIT ': "Ritarungo",
        'RKW ': "Arakwal",
        'RMS ': "Romansh",
        'RMY ': "Vlax Romani",
        'ROM ': "Romanian",
        'ROY ': "Romany",
        'RSY ': "Rusyn",
        'RTM ': "Rotuman",
        'RUA ': "Kinyarwanda",
        'RUN ': "Rundi",
        'RUP ': "Aromanian",
        'RUS ': "Russian",
        'SAD ': "Sadri",
        'SAN ': "Sanskrit",
        'SAS ': "Sasak",
        'SAT ': "Santali",
        'SAY ': "Sayisi",
        'SCN ': "Sicilian",
        'SCO ': "Scots",
        'SCS ': "North Slavey",
        'SEK ': "Sekota",
        'SEL ': "Selkup",
        'SFM ': "Small Flowery Miao",
        'SGA ': "Old Irish",
        'SGO ': "Sango",
        'SGS ': "Samogitian",
        'SHI ': "Tachelhit",
        'SHN ': "Shan",
        'SIB ': "Sibe",
        'SID ': "Sidamo",
        'SIG ': "Silte Gurage",
        'SKS ': "Skolt Sami",
        'SKY ': "Slovak",
        'SLA ': "Slavey",
        'SLV ': "Slovenian",
        'SML ': "Somali",
        'SMO ': "Samoan",
        'SNA ': "Sena",
        'SND ': "Sindhi",
        'SNH ': "Sinhala (Sinhalese)",
        'SNK ': "Soninke",
        'SOG ': "Sodo Gurage",
        'SOP ': "Songe",
        'SOT ': "Southern Sotho",
        'SQI ': "Albanian",
        'SRB ': "Serbian",
        'SRD ': "Sardinian",
        'SRK ': "Saraiki",
        'SRR ': "Serer",
        'SSL ': "South Slavey",
        'SSM ': "Southern Sami",
        'STQ ': "Saterland Frisian",
        'SUK ': "Sukuma",
        'SUN ': "Sundanese",
        'SUR ': "Suri",
        'SVA ': "Svan",
        'SVE ': "Swedish",
        'SWA ': "Swadaya Aramaic",
        'SWK ': "Swahili",
        'SWZ ': "Swati",
        'SXT ': "Sutu",
        'SXU ': "Upper Saxon",
        'SYL ': "Sylheti",
        'SYR ': "Syriac",
        'Syre': "Syriac, Estrangela script-variant",
        'Syrj': "Syriac, Western script-variant",
        'Syrn': "Syriac, Eastern script-variant",
        'SZL ': "Silesian",
        'TAB ': "Tabasaran",
        'TAJ ': "Tajiki",
        'TAM ': "Tamil",
        'TAT ': "Tatar",
        'TCR ': "TH-Cree",
        'TDD ': "Dehong Dai",
        'TEL ': "Telugu",
        'TET ': "Tetum",
        'TGL ': "Tagalog",
        'TGN ': "Tongan",
        'TGR ': "Tigre",
        'TGY ': "Tigrinya",
        'THA ': "Thai",
        'THT ': "Tahitian",
        'TIB ': "Tibetan",
        'TIV ': "Tiv",
        'TJL ': "Tai Laing",
        'TKM ': "Turkmen",
        'TLI ': "Tlingit",
        'TMH ': "Tamashek",
        'TMN ': "Temne",
        'TNA ': "Tswana",
        'TNE ': "Tundra Enets",
        'TNG ': "Tonga",
        'TOD ': "Todo",
        'TPI ': "Tok Pisin",
        'TRK ': "Turkish",
        'TSG ': "Tsonga",
        'TSJ ': "Tshangla",
        'TUA ': "Turoyo Aramaic",
        'TUL ': "Tulu",
        'TUM ': "Tumbuka",
        'TUV ': "Tuvin",
        'TVL ': "Tuvalu",
        'TWI ': "Twi",
        'TYZ ': "Tày",
        'TZM ': "Tamazight",
        'TZO ': "Tzotzil",
        'UDM ': "Udmurt",
        'UKR ': "Ukrainian",
        'UMB ': "Umbundu",
        'URD ': "Urdu",
        'USB ': "Upper Sorbian",
        'UYG ': "Uyghur",
        'UZB ': "Uzbek",
        'VEC ': "Venetian",
        'VEN ': "Venda",
        'VIT ': "Vietnamese",
        'VOL ': "Volapük",
        'VRO ': "Võro",
        'WA  ': "Wa",
        'WAG ': "Wagdi",
        'WAR ': "Waray-Waray",
        'WCI ': "Waci Gbe",
        'WCR ': "West-Cree",
        'WEL ': "Welsh",
        'WLF ': "Wolof",
        'WLN ': "Walloon",
        'WTM ': "Mewati",
        'XBD ': "Lü",
        'XHS ': "Xhosa",
        'XJB ': "Minjangbal",
        'XKF ': "Khengkha",
        'XOG ': "Soga",
        'XPE ': "Kpelle (Liberia)",
        'XUB ': "Bette Kuruma",
        'XUJ ': "Jennu Kuruma",
        'YAK ': "Sakha",
        'YAO ': "Yao",
        'YAP ': "Yapese",
        'YBA ': "Yoruba",
        'YCR ': "Y-Cree",
        'YGP ': "Gepo",
        'YIC ': "Yi Classic",
        'YIM ': "Yi Modern",
        'YNA ': "Aluo",
        'YWQ ': "Wuding-Luquan Yi",
        'ZEA ': "Zealandic",
        'ZGH ': "Standard Moroccan Tamazight",
        'ZHA ': "Zhuang",
        'ZHH ': "Chinese, Traditional, Hong Kong SAR",
        'ZHP ': "Chinese, Phonetic",
        'ZHS ': "Chinese, Simplified",
        'ZHT ': "Chinese, Traditional",
        'ZHTM': "Chinese, Traditional, Macao SAR",
        'ZND ': "Zande",
        'ZUL ': "Zulu",
        'ZZA ': "Zazaki",
    }

    def __init__(
        self,
        font: SpooledTemporaryFile | str,
        ft_font: freetypeFont,
        keep_open=False,
    ):
        self.ft_font = ft_font

        #
        # Read the font
        #
        if type(font) is SpooledTemporaryFile:
            font.seek(0)
            font_data = font.read()
            if not keep_open:
                font.close()
        else:
            font_file = open(font, "rb")
            font_data = font_file.read()
            if not keep_open:
                font_file.close()
        self.hb_face = hb.Face(font_data)
        self.hb_font = hb.Font(self.hb_face)

        #
        # Get tag lists: script, language, features
        #
        self._pos_features = hb._harfbuzz.ot_layout_language_get_feature_tags(
            self.hb_face, "GPOS"
        )
        self._sub_scripts = hb.ot_layout_table_get_script_tags(self.hb_face, "GSUB")
        self._sub_languages = ["dflt"]
        self._sub_features = []
        self._active_features = {}
        self.current_script_tag = ""
        self.current_language_tag = ""
        if "DFLT" in self._sub_scripts:
            self.current_script_tag = "DFLT"
        else:
            if len(self._sub_scripts):
                self.current_script_tag = self._sub_scripts[0]
        if self.current_script_tag:
            self._sub_languages.extend(
                hb.ot_layout_script_get_language_tags(
                    self.hb_face, "GSUB", script_index=self.current_script_index
                )
            )
            self.current_language_tag = "dflt"
            self._sub_features = hb._harfbuzz.ot_layout_language_get_feature_tags(
                self.hb_face,
                "GSUB",
                script_index=self.current_script_index,
                language_index=self.current_language_index,
            )
            self._sub_features = sorted(self._sub_features)
            self.set_default_features()

    def set_default_features(self) -> None:
        self._active_features.clear()
        if "ccmp" in self._sub_features:
            self._active_features["ccmp"] = True
        if "liga" in self._sub_features:
            self._active_features["liga"] = True
        if "calt" in self._sub_features:
            self._active_features["calt"] = True
        if "rlig" in self._sub_features:
            self._active_features["rlig"] = True
        if "locl" in self._sub_features:
            self._active_features["locl"] = True
        if "abvm" in self._pos_features:
            self._active_features["abvm"] = True
        if "blwm" in self._pos_features:
            self._active_features["blwm"] = True
        if "clig" in self._sub_features:
            self._active_features["clig"] = True
        if "curs" in self._sub_features:
            self._active_features["curs"] = True
        if "dist" in self._sub_features:
            self._active_features["dist"] = True
        if "rclt" in self._sub_features:
            self._active_features["rclt"] = True
        if "kern" in self._pos_features:
            self._active_features["kern"] = True
        if "mark" in self._pos_features:
            self._active_features["mark"] = True
        if "mkmk" in self._pos_features:
            self._active_features["mkmk"] = True

    def set_coordinates(self, d: dict) -> None:
        self.hb_font.set_variations(d)

    @property
    def current_script_index(self) -> int:
        try:
            return self._sub_scripts.index(self.current_script_tag)
        except ValueError:
            return harfbuzzFont.SCRIPT_DEFAULT

    @property
    def current_language_index(self) -> int:
        try:
            ind = self._sub_languages.index(self.current_language_tag)
            if ind == 0:
                ind = harfbuzzFont.LANG_DEFAULT
            else:
                ind -= 1
        except ValueError:
            ind = harfbuzzFont.LANG_DEFAULT
        return ind

    @property
    def sub_features(self) -> list:
        return self._sub_features

    @property
    def sub_scripts(self) -> list:
        return self._sub_scripts

    @property
    def sub_languages(self) -> list:
        return self._sub_languages

    #@property
    #def pos_features(self) -> list:
    #    return self._pos_features

    #@property
    #def all_features(self) -> list:
    #    result = []
    #    result.extend(self.sub_features)
    #    result.extend(self.pos_features)
    #    return result

    @property
    def active_features(self) -> list:
        return self._active_features
    
    @classmethod
    def expanded_script_name(self, tag: str) -> str:
        try:
            return tag + " - " + harfbuzzFont.SCRIPT_TAGS[tag]
        except KeyError:
            return tag

    @classmethod
    def expanded_language_name(self, tag: str) -> str:
        try:
            return tag + " - " + harfbuzzFont.LANGUAGE_TAGS[tag]
        except KeyError:
            return tag

    @classmethod
    def expanded_feature_name(self, tag) -> str:
        ss = tag
        prefix = tag[0:2]
        try:
            if prefix == "cv":
                ss = tag + " - " + "Character Variant " + tag[2:4]
            elif prefix == "ss":
                ss = tag + " - " + "Stylistic Set " + tag[2:4]
            else:
                ss = tag + " - " + harfbuzzFont.LAYOUT_TAGS[tag]
        except Exception:
            pass
        return ss

    @classmethod
    def tag_only(self, s) -> str:
        tag = s.split(" ")[0]
        if len(tag) == 2:
            tag += "  "
        elif len(tag) == 3:
            tag += " "
        assert len(tag) == 4, "Length of layout tag must be 4 (2)."
        return tag

    def select_script(self, s: str) -> None:
        """ If the currently selected language is not available for the newly
            selected script, change language to 'dflt'.
        """
        if s in self._sub_scripts:
            self.current_script_tag = s
        self.select_language(self.current_language_tag)

    def select_language(self, l: str) -> None:
        """ New tag should have been selected from a list of available tags.
            And set up feature list for newly selected language.
        """
        self.current_language_tag = ""
        self._sub_languages.clear()
        self._sub_languages.append("dflt")
        self._sub_languages.extend(
            hb.ot_layout_script_get_language_tags(
                self.hb_face, "GSUB", script_index=self.current_script_index
            )
        )
        if l in self._sub_languages:
            self.current_language_tag = l
        else:
            self.current_language_tag = "dflt"
        self._sub_features.clear()
        self._sub_features.extend(hb._harfbuzz.ot_layout_language_get_feature_tags(
            self.hb_face,
            "GSUB",
            script_index=self.current_script_index,
            language_index=self.current_language_index,
        ))
        self._sub_features = sorted(self._sub_features)
        self.set_default_features()

    def activate_feature(self, f: str, index: int = -1) -> None:
        """ Activate an OT feature. if index > 0, that is included
            as well, for indexed features like salt.
        """
        add_feature = False
        if f in self._pos_features:
            add_feature = True
        val = True
        if f in self._sub_features:
            # If index == 0, that means don't add the feature.
            if index > 0:
                val = index
                add_feature = True
            elif index < 0:
                add_feature = True
        if add_feature and not f in self._active_features:
            self._active_features[f] = val

    def deactivate_feature(self, f: str) -> None:
        try:
            del self._active_features[f]
        except KeyError:
            pass

    def get_shaped_names(self, s: str):
        """ Run shape() (below) on string s, and return:
            1. A list of glyph names
            2. Hb's buf.glyph_positions (all the metrics data we need)
        """
        buf = self.hb_buffer(s)
        if self.current_script_tag:
            buf.script = self.current_script_tag
            if self.current_language_tag:
                buf.language = self.current_language_tag
        info, pos = self.shape(buf)
        indices = []
        for i in info:
            indices.append(i.codepoint)
        return self.ft_font.indices_to_names(indices), pos

    def shape(self, buf):
        """ Run hb.shape() on a Harfbuzz buffer and return buf.glyph_infos
            and buf.glyph_positions exactly as hb returns them.
        """
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, self._active_features)
        return buf.glyph_infos, buf.glyph_positions

    def hb_buffer(self, s: str) -> hb.Buffer:
        """ Create an empty hb.Buffer and add string s to it.
        """
        buf = hb.Buffer.create()
        buf.add_str(s)
        return buf

    # @pyqtSlot()
    def reset_features(self):
        self.set_default_features()


class hbFeatureDialog(QDialog):
    def __init__(self, top_window, hb_font):
        super().__init__()
        self.valid = True
        self.top_window = top_window
        self.hb_font = hb_font
        self.setWindowTitle("Set an OpenType feature")
        self._layout = QVBoxLayout()
        self.input_layout = QHBoxLayout()
        QBtn = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.feature_list = []
        for s in self.hb_font._sub_features:
            self.feature_list.append(harfbuzzFont.expanded_feature_name(s))
        self.feature_list = sorted(self.feature_list)
        if len(self.feature_list):
            self.feature_box = QComboBox()
            for f in self.feature_list:
                self.feature_box.addItem(f)
            self.line_editor = QLineEdit()
            validator = QRegularExpressionValidator()
            re = QRegularExpression("\\b(on|off|[1-9]|[1-9][0-9])\\b")
            validator.setRegularExpression(re)
            self.line_editor.setValidator(validator)
            self.input_layout.addWidget(self.feature_box)
            self.input_layout.addWidget(self.line_editor)
            self._layout.addLayout(self.input_layout)
            self._layout.addWidget(self.buttonBox)
            self.setLayout(self._layout)
        else:
            self.valid = False

    @pyqtSlot()
    def accept(self) -> None:
        t = self.line_editor.text()
        current_tag = harfbuzzFont.tag_only(self.feature_box.currentText())
        val = None
        if len(t):
            try:
                val = int(t)
            except ValueError:
                if t == "on":
                    val = True
                elif t == "off":
                    val = False
        if val != None:
            self.hb_font.active_features[current_tag] = val
        super().accept()
