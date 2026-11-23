from decimal import Decimal

from subscriptions.services import convert_to_base, get_exchange_rates


def build_dashboard_summary(subscriptions, base_currency):
    subscriptions = list(subscriptions)
    currencies = {item.currency for item in subscriptions}
    rates = get_exchange_rates(base_currency, currencies)
    monthly_total = Decimal("0.00")
    annual_total = Decimal("0.00")
    convertible_count = 0
    unconverted = []
    category_totals = {}

    for subscription in subscriptions:
        monthly = convert_to_base(subscription.monthly_amount, subscription.currency, base_currency, rates)
        annual = convert_to_base(subscription.annual_amount, subscription.currency, base_currency, rates)
        if monthly is None or annual is None:
            unconverted.append(subscription.currency)
            continue
        convertible_count += 1
        monthly_total += monthly
        annual_total += annual
        category_name = subscription.category.name
        category_totals[category_name] = category_totals.get(category_name, Decimal("0.00")) + monthly

    return {
        "monthly_total": monthly_total.quantize(Decimal("0.01")),
        "annual_total": annual_total.quantize(Decimal("0.01")),
        "base_currency": base_currency,
        "convertible_count": convertible_count,
        "unconverted_currencies": sorted(set(unconverted)),
        "category_totals": sorted(category_totals.items(), key=lambda row: row[1], reverse=True),
    }
