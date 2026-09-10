"""
CSV Auto-Analyzer
=================

This is the main analysis engine of the project.

The engine is responsible for:

    1. Understanding CSV columns
    2. Detecting business meanings
    3. Detecting numeric / categorical / date fields
    4. Handling numbers stored as text
    5. Checking data quality
    6. Finding correlations
    7. Calculating business KPIs
    8. Generating business insights
    9. Supporting different types of business CSV files

IMPORTANT:

Real-world CSV files are often messy.

For example:

    "26,180.88"
    "$26,180.88"
    "₹26,180.88"
    "1,890"
    "10.52%"

may all be stored as TEXT.

This engine therefore tries to understand and safely
convert those values before performing calculations.
"""

import re

import numpy as np
import pandas as pd


# ============================================================
# 1. BUSINESS COLUMN RULES
# ============================================================
#
# These keywords help the analyzer understand the BUSINESS
# meaning of a column rather than only looking at its
# technical Python data type.
#
# The rules are intentionally broad because different
# companies use different column names.
# ============================================================

RULES = {

    "Financial Metric": [
        "revenue",
        "sales",
        "sale",
        "income",
        "amount",
        "price",
        "cost",
        "expense",
        "profit",
        "margin",
        "discount",
        "tax",
        "salary",
        "budget",
        "spend",
        "value",
        "gmv",
        "turnover",
        "order_value",
        "product_sales",
        "ordered_product_sales",
        "total_sales",
    ],


    "Quantity / Volume": [
        "quantity",
        "qty",
        "units",
        "unit",
        "volume",
        "count",
        "stock",
        "inventory",
        "orders",
        "order_count",
        "items",
        "item_count",
    ],


    "Traffic / Engagement": [
        "session",
        "sessions",
        "visitor",
        "visitors",
        "traffic",
        "page_views",
        "views",
        "impressions",
        "clicks",
        "visits",
    ],


    "Conversion Metric": [
        "conversion",
        "conversion_rate",
        "unit_session",
        "session_percentage",
        "conversion_percentage",
        "order_rate",
        "buy_rate",
    ],


    "Customer Identifier": [
        "customer_id",
        "customerid",
        "client_id",
        "clientid",
        "buyer_id",
        "buyerid",
        "customer_number",
    ],


    "Product Identifier": [
        "product_id",
        "productid",
        "item_id",
        "itemid",
        "sku",
        "asin",
        "product_code",
    ],


    "Order Identifier": [
        "order_id",
        "orderid",
        "invoice",
        "invoice_id",
        "transaction_id",
        "transactionid",
        "order_number",
    ],


    "Product Dimension": [
        "product",
        "item",
        "product_name",
        "item_name",
        "asin",
        "sku",
    ],


    "Category Dimension": [
        "category",
        "subcategory",
        "segment",
        "type",
        "class",
        "department",
        "group",
    ],


    "Geographic Dimension": [
        "country",
        "state",
        "city",
        "region",
        "area",
        "zone",
        "territory",
        "location",
        "market",
    ],


    "Time Dimension": [
        "date",
        "time",
        "year",
        "month",
        "quarter",
        "week",
        "day",
        "period",
    ],


    "Person / Contact": [
        "name",
        "first_name",
        "last_name",
        "email",
        "phone",
        "mobile",
        "address",
    ],


    "Percentage Metric": [
        "percentage",
        "percent",
        "rate",
        "ratio",
        "margin_pct",
        "growth_pct",
        "buy_box_percentage",
        "featured_offer_percentage",
    ],
}


# ============================================================
# 2. NORMALIZE COLUMN NAMES
# ============================================================
#
# Examples:
#
#     "Customer Name"
#         ↓
#     "customer_name"
#
#     "Ordered Product Sales"
#         ↓
#     "ordered_product_sales"
#
# This makes matching much more reliable.
# ============================================================

def normalize_name(name):

    text = str(name).strip().lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text,
    )

    return text.strip("_")


# ============================================================
# 3. CONVERT TEXT VALUES INTO NUMBERS
# ============================================================
#
# This is one of the most important functions in the project.
#
# CSV files frequently contain numbers as text.
#
# Examples:
#
#     "$26,180.88" → 26180.88
#     "₹45,000"    → 45000
#     "1,890"      → 1890
#     "10.52%"     → 10.52
#
# If a value cannot be converted, NaN is returned.
# ============================================================

def to_numeric_series(series):

    if pd.api.types.is_numeric_dtype(series):

        return pd.to_numeric(
            series,
            errors="coerce",
        )


    cleaned = (
        series
        .astype(str)
        .str.strip()
        .replace(
            {
                "": np.nan,
                "nan": np.nan,
                "None": np.nan,
                "null": np.nan,
                "N/A": np.nan,
                "NA": np.nan,
                "-": np.nan,
            }
        )
    )


    cleaned = (
        cleaned
        .str.replace(
            ",",
            "",
            regex=False,
        )
        .str.replace(
            "$",
            "",
            regex=False,
        )
        .str.replace(
            "₹",
            "",
            regex=False,
        )
        .str.replace(
            "€",
            "",
            regex=False,
        )
        .str.replace(
            "£",
            "",
            regex=False,
        )
        .str.replace(
            "%",
            "",
            regex=False,
        )
        .str.strip()
    )


    return pd.to_numeric(
        cleaned,
        errors="coerce",
    )


# ============================================================
# 4. CHECK WHETHER A COLUMN IS NUMERIC-LIKE
# ============================================================
#
# A column doesn't need to have dtype=float to be useful.
#
# If 80% or more of its non-empty values can be converted
# into numbers, we consider it numeric-like.
# ============================================================

def is_numeric_like(series):

    converted = to_numeric_series(
        series
    )

    non_empty = series.notna().sum()

    if non_empty == 0:

        return False

    valid_numbers = converted.notna().sum()

    percentage = (
        valid_numbers
        / non_empty
    )

    return percentage >= 0.80


# ============================================================
# 5. CLASSIFY ONE COLUMN
# ============================================================

def classify_column(
    name,
    series,
):

    normalized = normalize_name(
        name
    )


    priority = [

        "Customer Identifier",

        "Product Identifier",

        "Order Identifier",

        "Time Dimension",

        "Percentage Metric",

        "Conversion Metric",

        "Traffic / Engagement",

        "Financial Metric",

        "Quantity / Volume",

        "Product Dimension",

        "Category Dimension",

        "Geographic Dimension",

        "Person / Contact",
    ]


    # --------------------------------------------------------
    # BUSINESS NAME MATCHING
    # --------------------------------------------------------

    for business_type in priority:

        for keyword in RULES.get(
            business_type,
            [],
        ):

            keyword = normalize_name(
                keyword
            )


            if (
                normalized == keyword
                or keyword in normalized
            ):

                return (
                    business_type,
                    "High",
                    "Column name matched a business rule.",
                )


    # --------------------------------------------------------
    # DATETIME DETECTION
    # --------------------------------------------------------

    if pd.api.types.is_datetime64_any_dtype(
        series
    ):

        return (
            "Time Dimension",
            "High",
            "Column contains datetime values.",
        )


    # --------------------------------------------------------
    # DATE STORED AS TEXT
    # --------------------------------------------------------

    if series.dtype == "object":

        sample = (
            series
            .dropna()
            .astype(str)
            .head(100)
        )


        if len(sample):

            parsed = pd.to_datetime(
                sample,
                errors="coerce",
            )


            if (
                parsed.notna().mean()
                >= 0.80
            ):

                return (
                    "Time Dimension",
                    "Medium",
                    "Most sampled values look like dates.",
                )


    # --------------------------------------------------------
    # NUMERIC-LIKE COLUMN
    # --------------------------------------------------------

    if is_numeric_like(
        series
    ):

        return (
            "Numeric Measure",
            "Medium",
            "Column contains mostly numeric values.",
        )


    # --------------------------------------------------------
    # BOOLEAN
    # --------------------------------------------------------

    if pd.api.types.is_bool_dtype(
        series
    ):

        return (
            "Boolean Attribute",
            "High",
            "True/False column.",
        )


    # --------------------------------------------------------
    # DEFAULT
    # --------------------------------------------------------

    return (
        "Categorical Attribute",
        "Low",
        "Text column without a more specific business meaning.",
    )


# ============================================================
# 6. BUSINESS TYPE TABLE
# ============================================================

def business_types(df):

    rows = []


    for column in df.columns:

        (
            business_type,
            confidence,
            reason,
        ) = classify_column(
            column,
            df[column],
        )


        rows.append(
            {
                "Column": column,

                "Business Meaning": business_type,

                "Confidence": confidence,

                "Technical Type": str(
                    df[column].dtype
                ),

                "Unique Values": int(
                    df[column].nunique(
                        dropna=True
                    )
                ),

                "Reason": reason,
            }
        )


    return pd.DataFrame(
        rows
    )


# ============================================================
# 7. IDENTIFY COLUMN GROUPS
# ============================================================

def column_groups(df):

    numeric = []


    categorical = []


    dates = []


    for column in df.columns:

        series = df[column]


        # ----------------------------------------------------
        # REAL NUMERIC COLUMNS
        # ----------------------------------------------------

        if pd.api.types.is_numeric_dtype(
            series
        ):

            numeric.append(
                column
            )

            continue


        # ----------------------------------------------------
        # NUMERIC VALUES STORED AS TEXT
        # ----------------------------------------------------

        if is_numeric_like(
            series
        ):

            numeric.append(
                column
            )

            continue


        # ----------------------------------------------------
        # DATE DETECTION
        # ----------------------------------------------------

        name = str(
            column
        ).lower()


        if (
            "date" in name
            or "time" in name
            or "year" in name
        ):

            parsed = pd.to_datetime(
                series,
                errors="coerce",
            )


            if (
                parsed.notna().mean()
                >= 0.80
            ):

                dates.append(
                    column
                )

                continue


        # ----------------------------------------------------
        # CATEGORICAL
        # ----------------------------------------------------

        categorical.append(
            column
        )


    return (
        numeric,
        categorical,
        dates,
    )


# ============================================================
# 8. DATA QUALITY
# ============================================================

def quality(
    df,
    numeric,
):

    missing_cells = int(
        df.isna()
        .sum()
        .sum()
    )


    duplicate_rows = int(
        df.duplicated()
        .sum()
    )


    # --------------------------------------------------------
    # MISSING VALUES TABLE
    # --------------------------------------------------------

    missing_table = pd.DataFrame(
        {
            "Column": df.columns,

            "Missing Values": [
                int(
                    df[column]
                    .isna()
                    .sum()
                )

                for column in df.columns
            ],
        }
    )


    missing_table[
        "Missing %"
    ] = (
        missing_table[
            "Missing Values"
        ]
        / max(
            len(df),
            1,
        )
        * 100
    ).round(2)


    missing_table = (
        missing_table
        .sort_values(
            "Missing %",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )


    # --------------------------------------------------------
    # OUTLIER DETECTION
    # --------------------------------------------------------

    outlier_rows = []


    for column in numeric:

        series = to_numeric_series(
            df[column]
        ).dropna()


        if len(series) < 4:

            continue


        q1 = series.quantile(
            0.25
        )

        q3 = series.quantile(
            0.75
        )


        iqr = q3 - q1


        if iqr == 0:

            continue


        lower = (
            q1
            - (
                1.5
                * iqr
            )
        )


        upper = (
            q3
            + (
                1.5
                * iqr
            )
        )


        count = int(
            (
                (series < lower)
                | (series > upper)
            ).sum()
        )


        if count > 0:

            outlier_rows.append(
                {
                    "Column": column,

                    "Potential Outliers": count,

                    "Lower Bound": lower,

                    "Upper Bound": upper,
                }
            )


    outlier_columns = [

        "Column",

        "Potential Outliers",

        "Lower Bound",

        "Upper Bound",
    ]


    outlier_table = pd.DataFrame(
        outlier_rows,
        columns=outlier_columns,
    )


    # --------------------------------------------------------
    # HEALTH SCORE
    # --------------------------------------------------------

    total_cells = max(
        len(df)
        * max(
            len(df.columns),
            1,
        ),
        1,
    )


    missing_penalty = (
        missing_cells
        / total_cells
        * 50
    )


    duplicate_penalty = (
        duplicate_rows
        / max(
            len(df),
            1,
        )
        * 30
    )


    health_score = max(
        0,
        round(
            100
            - missing_penalty
            - duplicate_penalty,
            1,
        ),
    )


    outlier_cells = int(
        sum(
            row[
                "Potential Outliers"
            ]

            for row in outlier_rows
        )
    )


    # --------------------------------------------------------
    # RETURN BOTH THE NEW NAMES AND THE SHORT NAMES
    #
    # This keeps compatibility with app.py and the exporters.
    # --------------------------------------------------------

    return {

        "missing_cells": missing_cells,

        "duplicate_rows": duplicate_rows,

        "missing_table": missing_table,

        "outlier_table": outlier_table,

        "outlier_cells": outlier_cells,

        "health_score": health_score,


        # Compatibility names

        "missing": missing_cells,

        "duplicates": duplicate_rows,

        "outliers": outlier_cells,

        "score": health_score,
    }


# ============================================================
# 9. CORRELATION ANALYSIS
# ============================================================

def correlations(
    df,
    numeric,
):

    result_columns = [

        "Column A",

        "Column B",

        "Correlation",

        "Strength",
    ]


    if len(numeric) < 2:

        return pd.DataFrame(
            columns=result_columns
        )


    # --------------------------------------------------------
    # Create a temporary numeric dataframe.
    #
    # This is important because some CSV numeric columns
    # may actually be stored as text.
    # --------------------------------------------------------

    numeric_data = pd.DataFrame(
        index=df.index
    )


    for column in numeric:

        numeric_data[
            column
        ] = to_numeric_series(
            df[column]
        )


    matrix = numeric_data.corr()


    rows = []


    for i, first in enumerate(
        numeric
    ):

        for second in numeric[
            i + 1:
        ]:

            value = matrix.loc[
                first,
                second,
            ]


            if pd.isna(
                value
            ):

                continue


            if abs(value) >= 0.60:

                strength = (

                    "Strong"

                    if abs(value) >= 0.80

                    else "Moderate"
                )


                rows.append(
                    {
                        "Column A": first,

                        "Column B": second,

                        "Correlation": round(
                            float(value),
                            3,
                        ),

                        "Strength": strength,
                    }
                )


    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Never call sort_values("Correlation") on an empty
    # DataFrame that has no columns.
    # --------------------------------------------------------

    if not rows:

        return pd.DataFrame(
            columns=result_columns
        )


    result = pd.DataFrame(
        rows,
        columns=result_columns,
    )


    return (
        result
        .sort_values(
            "Correlation",
            key=lambda series: series.abs(),
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# 10. FIND A COLUMN BY BUSINESS MEANING
# ============================================================

def find_column(
    df,
    keywords,
):

    normalized_columns = {

        column: normalize_name(
            column
        )

        for column in df.columns
    }


    for keyword in keywords:

        keyword = normalize_name(
            keyword
        )


        for (
            column,
            normalized,
        ) in normalized_columns.items():

            if (
                normalized == keyword
                or keyword in normalized
            ):

                return column


    return None


# ============================================================
# 11. GET NUMERIC VALUE FROM A COLUMN
# ============================================================

def column_sum(
    df,
    column,
):

    if not column:

        return 0.0


    numeric_values = (
        to_numeric_series(
            df[column]
        )
    )


    return float(
        numeric_values
        .sum()
    )


# ============================================================
# 12. KPI ENGINE
# ============================================================

def calculate_kpis(df):

    kpis = []


    # --------------------------------------------------------
    # FIND IMPORTANT BUSINESS COLUMNS
    # --------------------------------------------------------

    revenue = find_column(
        df,
        [
            "revenue",
            "sales",
            "sales_amount",
            "selling_price",
            "ordered_product_sales",
            "product_sales",
            "total_sales",
            "gross_sales",
            "sales_value",
        ],
    )


    cost = find_column(
        df,
        [
            "cost",
            "expense",
            "cost_price",
            "purchase_cost",
            "total_cost",
        ],
    )


    profit = find_column(
        df,
        [
            "profit",
            "net_profit",
            "gross_profit",
            "total_profit",
        ],
    )


    quantity = find_column(
        df,
        [
            "quantity",
            "qty",
            "units",
            "units_ordered",
            "total_units",
            "items",
            "items_ordered",
        ],
    )


    order_id = find_column(
        df,
        [
            "order_id",
            "orderid",
            "invoice_id",
            "transaction_id",
            "order_number",
        ],
    )


    sessions = find_column(
        df,
        [
            "sessions",
            "session",
            "total_sessions",
        ],
    )


    page_views = find_column(
        df,
        [
            "page_views",
            "pageviews",
            "views",
            "page_view",
        ],
    )


    conversion = find_column(
        df,
        [
            "unit_session_percentage",
            "session_percentage",
            "conversion_rate",
            "conversion_percentage",
            "conversion",
        ],
    )


    buy_box = find_column(
        df,
        [
            "buy_box_percentage",
            "featured_offer_percentage",
            "buy_box",
            "featured_offer",
        ],
    )


    # ========================================================
    # SAFE KPI CREATOR
    # ========================================================

    def add_kpi(
        name,
        value,
        description,
        source,
        format_type,
    ):

        """
        Safely create a KPI.

        The value may be:

            12345

        or:

            "12,345"

        or:

            "$12,345.50"

        or:

            "45.6%"

        The function converts it before formatting.
        """


        # ----------------------------------------------------
        # CONVERT VALUE TO NUMBER
        # ----------------------------------------------------

        if isinstance(
            value,
            str,
        ):

            cleaned_value = (
                value
                .replace(
                    ",",
                    "",
                )
                .replace(
                    "$",
                    "",
                )
                .replace(
                    "₹",
                    "",
                )
                .replace(
                    "€",
                    "",
                )
                .replace(
                    "£",
                    "",
                )
                .replace(
                    "%",
                    "",
                )
                .strip()
            )


            try:

                numeric_value = float(
                    cleaned_value
                )

            except (
                ValueError,
                TypeError,
            ):

                numeric_value = None


        else:

            try:

                numeric_value = float(
                    value
                )

            except (
                ValueError,
                TypeError,
            ):

                numeric_value = None


        # ----------------------------------------------------
        # CREATE DISPLAY VALUE
        # ----------------------------------------------------

        if numeric_value is None:

            display_value = str(
                value
            )

        elif format_type == "currency":

            display_value = (
                f"₹{numeric_value:,.2f}"
            )

        elif format_type == "percentage":

            display_value = (
                f"{numeric_value:.2f}%"
            )

        elif format_type == "integer":

            display_value = (
                f"{numeric_value:,.0f}"
            )

        else:

            display_value = (
                f"{numeric_value:,.2f}"
            )


        # ----------------------------------------------------
        # SOURCE COLUMNS
        # ----------------------------------------------------

        if source is None:

            source_columns = []


        elif isinstance(
            source,
            list,
        ):

            source_columns = source


        else:

            source_columns = [
                source
            ]


        # ----------------------------------------------------
        # ADD KPI TO THE LIST
        # ----------------------------------------------------

        kpis.append(
            {
                "name": name,

                "value": numeric_value,

                "display_value": display_value,

                "description": description,

                "source_columns": source_columns,

                "format": format_type,
            }
        )


    # ========================================================
    # REVENUE
    # ========================================================

    if revenue:

        total_revenue = (
            column_sum(
                df,
                revenue,
            )
        )


        add_kpi(
            "Total Revenue",
            total_revenue,
            "Total sales/revenue recorded in the dataset.",
            [revenue],
            "currency",
        )


    # ========================================================
    # COST
    # ========================================================

    if cost:

        total_cost = (
            column_sum(
                df,
                cost,
            )
        )


        add_kpi(
            "Total Cost",
            total_cost,
            "Total cost or expense recorded in the dataset.",
            [cost],
            "currency",
        )


    # ========================================================
    # PROFIT
    # ========================================================

    if profit:

        total_profit = (
            column_sum(
                df,
                profit,
            )
        )


        add_kpi(
            "Total Profit",
            total_profit,
            "Total profit recorded in the dataset.",
            [profit],
            "currency",
        )


    elif (
        revenue
        and cost
    ):

        total_profit = (

            column_sum(
                df,
                revenue,
            )

            -

            column_sum(
                df,
                cost,
            )
        )


        add_kpi(
            "Total Profit",
            total_profit,
            "Revenue minus total cost.",
            [
                revenue,
                cost,
            ],
            "currency",
        )


    # ========================================================
    # PROFIT MARGIN
    # ========================================================

    if (
        revenue
        and cost
    ):

        total_revenue = (
            column_sum(
                df,
                revenue,
            )
        )


        total_cost = (
            column_sum(
                df,
                cost,
            )
        )


        if total_revenue != 0:

            margin = (

                (
                    total_revenue
                    - total_cost
                )

                / total_revenue

            ) * 100


            add_kpi(
                "Profit Margin",
                margin,
                "Profit expressed as a percentage of revenue.",
                [
                    revenue,
                    cost,
                ],
                "percentage",
            )


    # ========================================================
    # QUANTITY / UNITS
    # ========================================================

    if quantity:

        total_quantity = (
            column_sum(
                df,
                quantity,
            )
        )


        add_kpi(
            "Units / Quantity",
            total_quantity,
            "Total quantity or units recorded.",
            [quantity],
            "integer",
        )


    # ========================================================
    # ORDERS
    # ========================================================

    if order_id:

        orders = int(
            df[order_id]
            .nunique(
                dropna=True
            )
        )


        add_kpi(
            "Orders",
            orders,
            "Unique orders or transactions.",
            [order_id],
            "integer",
        )


        if (
            revenue
            and orders > 0
        ):

            average_order_value = (

                column_sum(
                    df,
                    revenue,
                )

                / orders
            )


            add_kpi(
                "Average Order Value",
                average_order_value,
                "Average revenue generated per unique order.",
                [
                    revenue,
                    order_id,
                ],
                "currency",
            )


    # ========================================================
    # SESSIONS
    # ========================================================

    if sessions:

        total_sessions = (
            column_sum(
                df,
                sessions,
            )
        )


        add_kpi(
            "Sessions",
            total_sessions,
            "Total customer sessions or visits.",
            [sessions],
            "integer",
        )


    # ========================================================
    # PAGE VIEWS
    # ========================================================

    if page_views:

        total_views = (
            column_sum(
                df,
                page_views,
            )
        )


        add_kpi(
            "Page Views",
            total_views,
            "Total product/page views recorded.",
            [page_views],
            "integer",
        )


    # ========================================================
    # CONVERSION RATE
    # ========================================================

    if conversion:

        converted = (
            to_numeric_series(
                df[conversion]
            )
        )


        valid_conversion = (
            converted.dropna()
        )


        if not valid_conversion.empty:

            average_conversion = (
                float(
                    valid_conversion.mean()
                )
            )


            add_kpi(
                "Average Conversion Rate",
                average_conversion,
                "Average conversion/session percentage.",
                [conversion],
                "percentage",
            )


    # ========================================================
    # BUY BOX / FEATURED OFFER
    # ========================================================

    if buy_box:

        converted = (
            to_numeric_series(
                df[buy_box]
            )
        )


        valid_buy_box = (
            converted.dropna()
        )


        if not valid_buy_box.empty:

            average_buy_box = (
                float(
                    valid_buy_box.mean()
                )
            )


            add_kpi(
                "Average Buy Box %",
                average_buy_box,
                "Average Buy Box or Featured Offer percentage.",
                [buy_box],
                "percentage",
            )


    return kpis


# ============================================================
# 13. BUSINESS INSIGHTS
# ============================================================

def generate_business_insights(
    df,
    result,
):

    insights = []


    quality_result = (
        result["quality"]
    )


    correlation_result = (
        result["correlations"]
    )


    kpis = result.get(
        "kpis",
        [],
    )


    # ========================================================
    # DATASET OVERVIEW
    # ========================================================

    insights.append(
        f"The dataset contains "
        f"{len(df):,} rows across "
        f"{len(df.columns):,} columns."
    )


    # ========================================================
    # DATA QUALITY
    # ========================================================

    if (
        quality_result[
            "missing_cells"
        ]
        > 0
    ):

        missing_table = (
            quality_result[
                "missing_table"
            ]
        )


        if not missing_table.empty:

            worst = (
                missing_table.iloc[0]
            )


            if (
                worst[
                    "Missing Values"
                ]
                > 0
            ):

                insights.append(
                    f"'{worst['Column']}' has "
                    f"the highest missing-data "
                    f"rate at "
                    f"{worst['Missing %']:.1f}%."
                )


    # ========================================================
    # DUPLICATES
    # ========================================================

    if (
        quality_result[
            "duplicate_rows"
        ]
        > 0
    ):

        insights.append(
            f"{quality_result['duplicate_rows']:,} "
            "duplicate rows were detected "
            "and should be reviewed."
        )


    # ========================================================
    # OUTLIERS
    # ========================================================

    if (
        quality_result[
            "outlier_cells"
        ]
        > 0
    ):

        insights.append(
            f"{quality_result['outlier_cells']:,} "
            "potential outlier values were "
            "detected in numeric fields."
        )


    # ========================================================
    # CORRELATION
    # ========================================================

    if (
        isinstance(
            correlation_result,
            pd.DataFrame,
        )

        and not correlation_result.empty
    ):

        first = (
            correlation_result.iloc[0]
        )


        direction = (

            "positive"

            if first[
                "Correlation"
            ] > 0

            else "negative"
        )


        insights.append(
            f"'{first['Column A']}' and "
            f"'{first['Column B']}' have "
            f"a {direction} relationship "
            f"(correlation "
            f"{first['Correlation']:.2f})."
        )


    # ========================================================
    # PROFIT MARGIN
    # ========================================================

    for kpi in kpis:

        if (
            kpi.get(
                "name"
            )
            == "Profit Margin"
        ):

            margin = kpi.get(
                "value"
            )


            if margin is None:

                continue


            if margin < 0:

                insights.append(
                    "The calculated profit "
                    "margin is negative, "
                    "which indicates costs "
                    "exceed revenue."
                )


            elif margin < 10:

                insights.append(
                    "The calculated profit "
                    "margin is relatively low "
                    "and may deserve closer "
                    "cost analysis."
                )


            elif margin >= 30:

                insights.append(
                    "The calculated profit "
                    "margin is high; investigate "
                    "which products, customers "
                    "or segments are driving it."
                )


    # ========================================================
    # AMAZON / E-COMMERCE INSIGHTS
    # ========================================================

    kpi_names = {
        item.get("name")
        for item in kpis
    }


    if (
        "Sessions"
        in kpi_names
    ):

        session_kpi = next(
            (
                item
                for item in kpis
                if item.get(
                    "name"
                )
                == "Sessions"
            ),
            None,
        )


        if session_kpi:

            sessions_value = (
                session_kpi.get(
                    "value"
                )
            )


            if (
                sessions_value is not None
                and sessions_value > 0
            ):

                insights.append(
                    "The dataset contains "
                    f"{sessions_value:,.0f} "
                    "customer sessions, "
                    "so traffic volume can be "
                    "used to evaluate conversion "
                    "and sales performance."
                )


    if (
        "Average Conversion Rate"
        in kpi_names
    ):

        conversion_kpi = next(
            (
                item
                for item in kpis
                if item.get(
                    "name"
                )
                == "Average Conversion Rate"
            ),
            None,
        )


        if conversion_kpi:

            conversion_value = (
                conversion_kpi.get(
                    "value"
                )
            )


            if conversion_value is not None:

                if conversion_value < 5:

                    insights.append(
                        "The average conversion rate "
                        "is relatively low. Improving "
                        "product presentation, pricing, "
                        "traffic quality or listing "
                        "content may be worth investigating."
                    )


                elif conversion_value >= 15:

                    insights.append(
                        "The average conversion rate "
                        "is relatively strong, suggesting "
                        "the traffic reaching these listings "
                        "is converting effectively."
                    )


    # ========================================================
    # FALLBACK INSIGHT
    # ========================================================

    if len(insights) == 1:

        insights.append(
            "No major business anomalies were "
            "identified from the available fields. "
            "The dataset can be explored further "
            "using the interactive charts and "
            "business classification."
        )


    return insights


# ============================================================
# 14. PUBLIC KPI FUNCTION
# ============================================================
#
# app.py can import:
#
#     from analysis.engine import kpis
#
# ============================================================

def kpis(df):

    return calculate_kpis(
        df
    )


# ============================================================
# 15. PUBLIC INSIGHTS FUNCTION
# ============================================================
#
# This wrapper keeps compatibility with app.py.
#
# app.py can call:
#
#     insights(
#         df,
#         quality,
#         correlations,
#         kpis,
#     )
# ============================================================

def insights(
    df,
    quality_result,
    correlation_result,
    kpi_result,
):

    result = {

        "quality": quality_result,

        "correlations": correlation_result,

        "kpis": kpi_result,
    }


    return generate_business_insights(
        df,
        result,
    )


# ============================================================
# 16. MASTER ANALYSIS FUNCTION
# ============================================================
#
# app.py calls this function.
#
# It runs all major analysis components and returns one
# dictionary containing everything the application needs.
# ============================================================

def analyze(df):

    numeric, categorical, dates = (
        column_groups(
            df
        )
    )


    result = {

        "numeric": numeric,

        "categorical": categorical,

        "dates": dates,


        "business": business_types(
            df
        ),


        "quality": quality(
            df,
            numeric,
        ),


        "correlations": correlations(
            df,
            numeric,
        ),
    }


    # --------------------------------------------------------
    # CALCULATE KPIs
    # --------------------------------------------------------

    result[
        "kpis"
    ] = calculate_kpis(
        df
    )


    # --------------------------------------------------------
    # GENERATE BUSINESS INSIGHTS
    # --------------------------------------------------------

    result[
        "insights"
    ] = generate_business_insights(
        df,
        result,
    )


    return result