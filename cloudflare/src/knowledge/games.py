FIRERED_POOL = [
    "Venusaur","Charizard","Blastoise","Raichu","Nidoking","Nidoqueen","Clefable","Ninetales","Vileplume",
    "Primeape","Arcanine","Poliwrath","Alakazam","Machamp","Golem","Slowbro","Magneton","Dodrio",
    "Dewgong","Muk","Cloyster","Gengar","Hypno","Exeggutor","Marowak","Hitmonlee","Hitmonchan",
    "Weezing","Rhydon","Chansey","Kangaskhan","Starmie","Scyther","Jynx","Electabuzz","Pinsir",
    "Tauros","Gyarados","Lapras","Vaporeon","Jolteon","Flareon","Porygon","Aerodactyl","Snorlax","Dragonite"
]

GAME_GUIDES = {
    "pokemon firered": {
        "aliases": ["pokemon firered", "fire red", "firered", "pokemon fire red"],
        "summary": "Pokémon FireRed é um remake de Pokémon Red ambientado em Kanto, com os 151 Pokémon clássicos como base e conteúdo adicional após a Liga.",
        "team_pool": FIRERED_POOL,
        "tips": ["Misture cobertura de tipos.", "Considere disponibilidade durante a campanha.", "Evitar lendários costuma deixar o time mais variado."]
    }
}

GAMES = {
    "minecraft": {"platforms":["pc"],"genres":["sandbox","sobrevivencia","criacao"],"modes":["singleplayer","multiplayer"],"weight":"leve-medio","summary":"Sandbox de exploração, construção e sobrevivência com liberdade enorme para jogar sozinho ou com amigos.","tags":["criativo","relaxante","coop","construcao"]},
    "stardew valley": {"platforms":["pc"],"genres":["simulacao","fazenda","rpg"],"modes":["singleplayer","coop"],"weight":"leve","summary":"Simulador de fazenda com rotina, relações, exploração e progressão tranquila.","tags":["relaxante","leve","pixel","coop"]},
    "terraria": {"platforms":["pc"],"genres":["sandbox","acao","sobrevivencia"],"modes":["singleplayer","multiplayer"],"weight":"leve","summary":"Exploração 2D, mineração, crafting e chefes; parece simples até você abrir a wiki e perceber que perdeu a tarde.","tags":["leve","coop","exploracao","chefes"]},
    "hades": {"platforms":["pc"],"genres":["roguelike","acao"],"modes":["singleplayer"],"weight":"leve-medio","summary":"Roguelike de ação rápido, com narrativa que avança a cada tentativa e combate muito polido.","tags":["rapido","mitologia","replay","historia"]},
    "hollow knight": {"platforms":["pc"],"genres":["metroidvania","acao"],"modes":["singleplayer"],"weight":"leve","summary":"Metroidvania atmosférico com exploração, combate exigente e mundo interligado.","tags":["dificil","exploracao","atmosfera","2d"]},
    "celeste": {"platforms":["pc"],"genres":["plataforma"],"modes":["singleplayer"],"weight":"leve","summary":"Plataforma preciso e difícil, com capítulos curtos e uma história centrada em ansiedade, esforço e persistência.","tags":["leve","dificil","pixel","historia"]},
    "portal 2": {"platforms":["pc"],"genres":["puzzle","aventura"],"modes":["singleplayer","coop"],"weight":"leve","summary":"Puzzle em primeira pessoa com portais, humor excelente e campanha cooperativa separada.","tags":["leve","puzzle","coop","humor"]},
    "left 4 dead 2": {"platforms":["pc"],"genres":["fps","acao"],"modes":["coop","multiplayer"],"weight":"leve","summary":"FPS cooperativo contra hordas de infectados; direto, rejogável e ótimo em grupo.","tags":["leve","coop","zumbi","fps"]},
    "valorant": {"platforms":["pc"],"genres":["fps","competitivo"],"modes":["multiplayer"],"weight":"leve-medio","summary":"FPS tático competitivo 5v5 com agentes e habilidades.","tags":["competitivo","online","fps","equipe"]},
    "league of legends": {"platforms":["pc"],"genres":["moba","competitivo"],"modes":["multiplayer"],"weight":"leve","summary":"MOBA competitivo em equipe com enorme elenco de campeões e curva de aprendizado longa.","tags":["competitivo","online","equipe","leve"]},
    "the witcher 3": {"platforms":["pc"],"genres":["rpg","acao","mundo aberto"],"modes":["singleplayer"],"weight":"pesado","summary":"RPG de mundo aberto focado em narrativa, escolhas, contratos de monstros e exploração.","tags":["historia","mundo aberto","fantasia","longo"]},
    "skyrim": {"platforms":["pc"],"genres":["rpg","mundo aberto"],"modes":["singleplayer"],"weight":"medio","summary":"RPG de fantasia em mundo aberto com liberdade para explorar, criar personagem e ignorar a missão principal por cinquenta horas.","tags":["fantasia","mods","mundo aberto","exploracao"]},
    "fallout new vegas": {"platforms":["pc"],"genres":["rpg","mundo aberto"],"modes":["singleplayer"],"weight":"leve-medio","summary":"RPG pós-apocalíptico conhecido por escolhas, facções e diálogos com bastante impacto.","tags":["rpg","escolhas","historia","mods"]},
    "mass effect legendary edition": {"platforms":["pc"],"genres":["rpg","acao","ficcao cientifica"],"modes":["singleplayer"],"weight":"pesado","summary":"Trilogia de RPG sci-fi com escolhas persistentes, tripulação e narrativa cinematográfica.","tags":["historia","sci-fi","escolhas","longo"]},
    "disco elysium": {"platforms":["pc"],"genres":["rpg","narrativo"],"modes":["singleplayer"],"weight":"leve-medio","summary":"RPG investigativo praticamente sem combate tradicional, centrado em diálogo, personalidade e escolhas.","tags":["texto","investigacao","adulto","historia"]},
    "baldurs gate 3": {"platforms":["pc"],"genres":["rpg","turnos"],"modes":["singleplayer","coop"],"weight":"pesado","summary":"RPG de turnos baseado em D&D, com muita liberdade, escolhas e cooperação.","tags":["rpg","coop","fantasia","escolhas"]},
    "civilization vi": {"platforms":["pc"],"genres":["estrategia","turnos"],"modes":["singleplayer","multiplayer"],"weight":"medio","summary":"Estratégia 4X por turnos sobre construir e desenvolver uma civilização ao longo da história.","tags":["estrategia","turnos","longo","historico"]},
    "age of empires ii definitive edition": {"platforms":["pc"],"genres":["estrategia","rts"],"modes":["singleplayer","multiplayer"],"weight":"leve-medio","summary":"RTS clássico de construção de base, economia e batalhas históricas.","tags":["estrategia","rts","classico","multiplayer"]},
    "rimworld": {"platforms":["pc"],"genres":["simulacao","estrategia"],"modes":["singleplayer"],"weight":"leve","summary":"Simulador de colônia emergente em que cada desastre vira história para contar.","tags":["leve","gestao","sandbox","replay"]},
    "factorio": {"platforms":["pc"],"genres":["automacao","estrategia","sandbox"],"modes":["singleplayer","multiplayer"],"weight":"leve-medio","summary":"Construção e otimização de fábricas automatizadas; excelente se planilhas lhe parecem entretenimento.","tags":["automacao","logica","coop","sandbox"]},
    "dont starve together": {"platforms":["pc"],"genres":["sobrevivencia","sandbox"],"modes":["coop","multiplayer"],"weight":"leve","summary":"Sobrevivência cooperativa estilizada, punitiva e cheia de sistemas para aprender.","tags":["leve","coop","sobrevivencia","dificil"]},
    "deep rock galactic": {"platforms":["pc"],"genres":["fps","coop"],"modes":["coop","multiplayer"],"weight":"medio","summary":"FPS cooperativo de anões espaciais minerando cavernas procedurais e enfrentando criaturas.","tags":["coop","fps","humor","equipe"]},
    "dead cells": {"platforms":["pc"],"genres":["roguelike","metroidvania","acao"],"modes":["singleplayer"],"weight":"leve","summary":"Ação 2D rápida, progressão roguelite e bastante repetição voluntária do sofrimento.","tags":["leve","dificil","replay","2d"]},
    "undertale": {"platforms":["pc"],"genres":["rpg","narrativo"],"modes":["singleplayer"],"weight":"leve","summary":"RPG curto e peculiar em que combate e escolhas morais se misturam de formas pouco convencionais.","tags":["leve","historia","curto","pixel"]},
    "slay the spire": {"platforms":["pc"],"genres":["cartas","roguelike","estrategia"],"modes":["singleplayer"],"weight":"leve","summary":"Deckbuilder roguelike com partidas estratégicas e muita rejogabilidade.","tags":["leve","cartas","estrategia","replay"]}
}
