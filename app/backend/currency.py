"""Currency display options. Rates are intentionally not hard-coded."""
CURRENCIES = {
    "USD":"$", "EUR":"€", "GBP":"£", "INR":"₹", "CAD":"C$", "AUD":"A$", "NZD":"NZ$",
    "SGD":"S$", "HKD":"HK$", "JPY":"¥", "CNY":"¥", "KRW":"₩", "AED":"د.إ", "SAR":"﷼",
    "QAR":"﷼", "KWD":"د.ك", "BHD":"ب.د", "OMR":"﷼", "ZAR":"R", "BRL":"R$", "MXN":"MX$",
    "CHF":"CHF ", "SEK":"kr ", "NOK":"kr ", "DKK":"kr ", "PLN":"zł ", "THB":"฿", "MYR":"RM",
    "IDR":"Rp", "PHP":"₱", "VND":"₫", "TRY":"₺", "ILS":"₪", "EGP":"E£", "NGN":"₦"
}

def format_currency(value, currency="USD"):
    symbol=CURRENCIES.get(currency,currency+" ")
    try:return f"{symbol}{float(value):,.2f}"
    except (TypeError,ValueError):return str(value)
