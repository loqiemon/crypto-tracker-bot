COIN_IDS: dict[str, str] = {
    "btc": "bitcoin",
    "eth": "ethereum",
    "sol": "solana",
    "doge": "dogecoin",
    "ton": "the-open-network",
}

COIN_NAMES: dict[str, str] = {
    "btc": "Bitcoin",
    "eth": "Ethereum",
    "sol": "Solana",
    "doge": "Dogecoin",
    "ton": "Toncoin",
}

COIN_EMOJI: dict[str, str] = {
    "btc": "₿",
    "eth": "Ξ",
    "sol": "◎",
    "doge": "Ð",
    "ton": "💎",
}

COIN_ORDER: list[str] = ["btc", "eth", "sol", "doge", "ton"]

REVERSE_IDS: dict[str, str] = {v: k for k, v in COIN_IDS.items()}