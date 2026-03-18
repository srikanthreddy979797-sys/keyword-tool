# input_module.py

COUNTRY_GEO_MAP = {
    "india": 356,
    "usa": 2840,
    "united states": 2840,
    "uk": 2826,
    "united kingdom": 2826,
    "canada": 2124,
    "australia": 2036
}

LANGUAGE_CONSTANT = "languageConstants/1000"  # English


def get_user_input():
    keyword = input("Enter keyword: ").strip().lower()
    country = input("Enter country: ").strip().lower()
    return keyword, country


def validate_input(keyword, country):
    if not keyword:
        raise ValueError("Keyword cannot be empty")

    if country not in COUNTRY_GEO_MAP:
        raise ValueError(f"Unsupported country: {country}")

    return True


def prepare_input_data(keyword, country):
    geo_id = COUNTRY_GEO_MAP[country]

    return {
        "keyword": keyword,
        "country": country,
        "geo_id": geo_id,
        "geo_target": f"geoTargetConstants/{geo_id}",
        "language": LANGUAGE_CONSTANT
    }


def main():
    keyword, country = get_user_input()
    validate_input(keyword, country)

    prepared_data = prepare_input_data(keyword, country)

    print("\n✅ Prepared Input Data:")
    print(prepared_data)


if __name__ == "__main__":
    main()
