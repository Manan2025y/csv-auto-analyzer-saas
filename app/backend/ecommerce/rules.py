"""Amazon/Walmart-oriented semantic helpers."""

AMAZON_TERMS = ("asin", "sessions", "page views", "buy box", "units ordered", "ordered product sales", "unit session percentage")
WALMART_TERMS = ("item id", "sku", "walmart", "gmv", "units sold", "orders", "conversion")


def detect_ecommerce_platform(columns):
    text = " ".join(str(c).lower() for c in columns)
    amazon = sum(term in text for term in AMAZON_TERMS)
    walmart = sum(term in text for term in WALMART_TERMS)
    if amazon >= 2 and amazon > walmart:
        return "Amazon", amazon, walmart
    if walmart >= 2 and walmart > amazon:
        return "Walmart", amazon, walmart
    if amazon or walmart:
        return "E-commerce", amazon, walmart
    return "General business", amazon, walmart
