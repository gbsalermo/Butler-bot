"""Comentários curtos do Butler para a previsão do tempo.

A classificação usa os dados do Open-Meteo para traduzir o cenário em uma frase
curta e útil. Para "hoje", condições atuais têm prioridade sobre a máxima do
dia para evitar descrever uma manhã fresca/nublada como se já estivesse quente.
"""


def _number(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _period(heading):
    text = (heading or "").lower()
    if "amanhã" in text or "amanha" in text:
        return "Amanhã"
    if "hoje" in text:
        return "Hoje"
    return "Pelo jeito"


def _pick(options, forecast, city, category):
    """Escolhe variante de forma estável, mas diferente entre dias/cidades."""
    seed = f"{forecast.get('date','')}|{city}|{category}"
    index = sum((pos + 1) * ord(char) for pos, char in enumerate(seed)) % len(options)
    return options[index]


def forecast_comment(forecast, heading="Tempo", city=""):
    """Retorna uma frase coloquial coerente com o cenário do dia."""
    rain = _number(forecast.get("rain_sum"), 0.0) or 0.0
    rain_hours = _number(forecast.get("rain_hours"), 0.0) or 0.0
    cloud = _number(forecast.get("cloud_cover_mean"))
    tmax = _number(forecast.get("temperature_max"))
    wind = _number(forecast.get("wind_max"), 0.0) or 0.0
    code = int(forecast.get("weather_code", -1) or -1)
    period = _period(heading)

    current_temp = _number(forecast.get("current_temperature"))
    current_cloud = _number(forecast.get("current_cloud_cover"))
    current_code_raw = forecast.get("current_weather_code")
    try:
        current_code = int(current_code_raw) if current_code_raw is not None else None
    except (TypeError, ValueError):
        current_code = None

    if code in {95, 96, 99} or rain >= 15:
        category = "storm"
        options = (
            f"{period} o céu parece estar de mau humor. Se for sair, vai preparado para chuva de verdade.",
            f"{period} tem cara de dia em que o guarda-chuva deixa de ser acessório e vira equipamento obrigatório.",
            f"{period} a previsão está bem molhada. Melhor não contar com a sorte para chegar seco.",
        )
    elif rain >= 5 or rain_hours >= 4:
        category = "rain"
        options = (
            f"{period} a chuva deve aparecer com vontade. Leva alguma proteção e não confia muito naquele 'é só uma garoinha'.",
            f"{period} está com uma bela cara de chuva. Guarda-chuva na mão evita correr igual condenado depois.",
            f"{period} o céu provavelmente vai abrir a torneira em algum momento. Melhor sair prevenido.",
        )
    elif rain > 0.1:
        category = "light_rain"
        options = (
            f"{period} pode cair uma chuva rápida. Nada apocalíptico, mas é bom não ser pego de surpresa.",
            f"{period} existe chance de umas gotas atrapalharem o roteiro. Uma proteção leve já resolve a novela.",
            f"{period} a chuva pode dar uma passada por aí. Não parece o fim do mundo, só o suficiente para incomodar.",
        )
    elif (
        period == "Hoje"
        and current_temp is not None
        and (
            current_code in {3, 45, 48}
            or (current_cloud is not None and current_cloud >= 75)
        )
    ):
        category = "current_cloudy"
        if current_temp <= 24 and tmax is not None and tmax >= 30:
            options = (
                "Agora está nublado e mais fresco. Pode esquentar bastante mais tarde, então a máxima do dia não descreve este momento.",
                "O começo do dia está mais fechado e fresco. A temperatura pode subir depois, mas por enquanto o sol não está mandando em nada.",
                "Neste momento o céu está bem nublado e a temperatura mais baixa. O calor pode aparecer mais tarde, não agora.",
            )
        else:
            options = (
                "Agora o céu está bem fechado. Mesmo que a previsão mude ao longo do dia, neste momento o cenário é de bastante nuvem.",
                "Por enquanto está nublado. A previsão do restante do dia pode melhorar, mas o céu agora está fazendo hora extra.",
                "Neste momento tem bastante nuvem no céu. Melhor separar o clima de agora da tendência para o resto do dia.",
            )
    elif (
        period == "Hoje"
        and current_temp is not None
        and current_temp <= 24
        and tmax is not None
        and tmax >= 30
    ):
        category = "current_cool_then_hot"
        options = (
            "Agora está mais fresco, mas a temperatura deve subir ao longo do dia. A máxima é para mais tarde, não para este momento.",
            "A manhã ainda está comportada na temperatura. O calor deve aparecer mais tarde, então não confunde a máxima com o clima de agora.",
            "Por enquanto a temperatura está agradável. Mais tarde deve esquentar bem, mas ainda não chegou nessa parte do roteiro.",
        )
    elif tmax is not None and tmax >= 33 and (cloud is None or cloud <= 55):
        category = "very_hot"
        options = (
            f"{period} o sol deve trabalhar sem nenhuma consideração pelos outros. Água, sombra e juízo ajudam bastante.",
            f"{period} promete aquele calor que faz até o asfalto parecer pessoal. Se hidrata e procura sombra quando der.",
            f"{period} tem tudo para ser um dia de sol castigando. Garrafa d'água por perto e menos heroísmo no calor.",
        )
    elif tmax is not None and tmax >= 30 and (cloud is None or cloud <= 65):
        category = "hot"
        options = (
            f"{period} deve esquentar bem. Não precisa declarar guerra ao sol: água e sombra já fazem um bom serviço.",
            f"{period} o calor vem aí com certa falta de educação. Vale se hidratar direito durante o dia.",
            f"{period} parece dia de roupa leve e água por perto. O sol não deve facilitar muito.",
        )
    elif wind >= 35:
        category = "windy"
        options = (
            f"{period} o vento deve aparecer com disposição. Segura o boné e evita confiar em papel solto.",
            f"{period} vai ventar bem. Pelo menos o cabelo ganha uma personalidade nova sem cobrar nada.",
            f"{period} o vento pode incomodar um pouco. Nada de deixar coisa leve dando sopa por aí.",
        )
    elif tmax is not None and tmax <= 22:
        category = "cool"
        options = (
            f"{period} deve ficar mais fresco. Talvez seja um raro dia em que sair no sol não pareça uma punição.",
            f"{period} a temperatura vem mais comportada. Se você sente frio fácil, uma camada extra não é má ideia.",
            f"{period} promete um clima mais fresco e civilizado. Aproveita enquanto dura.",
        )
    elif cloud is not None and cloud >= 75:
        category = "cloudy"
        options = (
            f"{period} o céu deve passar boa parte do tempo fechado. Pelo menos o sol resolveu diminuir o expediente.",
            f"{period} tem cara de dia cinza, com bastante nuvem fazendo hora extra.",
            f"{period} o céu deve ficar bem encoberto. Não é exatamente fotogênico, mas também não é motivo para cancelar o dia.",
        )
    else:
        category = "pleasant"
        options = (
            f"{period} o tempo parece relativamente comportado. Um daqueles dias em que o clima talvez não tente sabotar seus planos.",
            f"{period} a previsão está tranquila. Dá para tocar o dia sem montar uma operação especial contra o tempo.",
            f"{period} o clima parece colaborar. Aproveita, porque até a meteorologia às vezes resolve ajudar.",
        )

    return _pick(options, forecast, city, category)
