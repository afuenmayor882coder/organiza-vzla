"""
NIIF (IFRS) cash-flow classification helpers.
Used when auto-classifying imported bank statement rows.
"""

from utils.constants import BANK_KEYWORD_MAP


def classify_description(description: str) -> tuple[str, str]:
    """
    Attempt to classify a bank statement description into a NIIF category
    and subcategory by matching keywords.

    Returns ("Sin Clasificar", "Sin Clasificar") if no keyword matches.
    """
    text = description.lower().strip()
    for keyword, (category, subcategory) in BANK_KEYWORD_MAP.items():
        if keyword in text:
            return category, subcategory
    return "Sin Clasificar", "Sin Clasificar"


def classify_dataframe(df, description_column: str = "description"):
    """
    Takes a pandas DataFrame with a description column and adds
    `niif_category` and `niif_subcategory` columns based on keyword matching.
    Modifies the DataFrame in place and returns it.
    """
    categories = []
    subcategories = []
    for desc in df[description_column].fillna(""):
        cat, sub = classify_description(str(desc))
        categories.append(cat)
        subcategories.append(sub)
    df["niif_category"] = categories
    df["niif_subcategory"] = subcategories
    return df
