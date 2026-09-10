"""Lightweight UI translation foundation."""
TRANSLATIONS = {
    "en": {"app_name": "CSV Auto-Analyzer", "upload": "Upload CSV", "dashboard": "Dashboard", "studio": "Chart Studio", "forecast": "Forecast", "intelligence": "Data Intelligence", "reports": "Reports", "saved": "Saved Dashboards", "settings": "Settings"},
    "hi": {"app_name": "CSV Auto-Analyzer", "upload": "CSV अपलोड करें", "dashboard": "डैशबोर्ड", "studio": "चार्ट स्टूडियो", "forecast": "पूर्वानुमान", "intelligence": "डेटा इंटेलिजेंस", "reports": "रिपोर्ट", "saved": "सेव किए गए डैशबोर्ड", "settings": "सेटिंग्स"},
    "es": {"app_name": "CSV Auto-Analyzer", "upload": "Subir CSV", "dashboard": "Panel", "studio": "Estudio de gráficos", "forecast": "Pronóstico", "intelligence": "Inteligencia de datos", "reports": "Informes", "saved": "Paneles guardados", "settings": "Configuración"},
}

def t(key: str, language: str = "en") -> str:
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, key)
